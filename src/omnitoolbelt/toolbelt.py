from typing import Any, Callable, Dict, Optional, List, Tuple, Union, get_type_hints
import inspect
from functools import wraps
import asyncio
from dataclasses import dataclass
import warnings

try:
    from apiomorphic import ApiFormat, format_tool_schema

    APIOMORPHIC_AVAILABLE = True
except ImportError:
    APIOMORPHIC_AVAILABLE = False
    ApiFormat = Any


@dataclass
class ToolDefinition:
    """Defines a callable tool.

    Attributes:
        callable: The actual Python function to execute
        description: A clear description for the user about what the tool does
        parameters: JSON schema defining the expected parameters structure
    """

    callable: Callable[..., Any]
    description: str
    parameters: Dict[str, Any]  # JSON Schema structure
    source_file_path: Optional[str]
    source_line_index: Optional[int]

    def __post_init__(self):
        # Validate that parameters contains a valid JSON schema structure
        required_schema_keys = {"type", "properties"}
        if not all(key in self.parameters for key in required_schema_keys):
            raise ValueError("parameters must contain a valid JSON schema")


def get_func_description(func):
    return (inspect.getdoc(func) or "",)


def get_json_type(typ: Any) -> str:
    """Convert Python type to JSON schema type"""
    return {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }.get(typ, "string")


def get_func_parameters(func):
    # Generate parameter schema from type hints
    hints = get_type_hints(func)
    if "return" in hints:
        del hints["return"]

    return {
        "type": "object",
        "properties": {
            param: {"type": get_json_type(typ)} for param, typ in hints.items()
        },
        "required": list(hints.keys()),
    }


class Toolbelt:
    """Registry and executor for callable tools"""

    def __init__(self):
        self._tool_definitions: Dict[str, ToolDefinition]

    def tool(self, name: Optional[str] = None) -> Callable:
        """Register a function as an callable tool"""

        def decorator(func: Callable) -> Callable:
            nonlocal name
            if name is None:
                name = func.__name__

            source_file_path = source_line_index = None
            try:
                frame = inspect.currentframe()
                if frame is not None:
                    frame = frame.f_back
                    if frame is not None:
                        source_file_path = frame.f_code.co_filename
                source_line_index = frame.f_lineno
            except Exception as e:
                warnings.warn(
                    f'Failed to get source location for tool ="{name}": {str(e)}',
                    RuntimeWarning,
                )
            finally:
                if frame is not None:
                    del frame
            if name in self._tool_definitions:
                existing = self._tool_definitions[name]
                old_location_msg = (
                    f"{existing.source_file_path}:{existing.source_line_index}"
                )
                new_location_msg = f"{source_file_path}:{source_line_index}"
                warnings.warn(
                    f'Tool "{name}" defined at {old_location_msg} is being overwritten by definition at {new_location_msg}\n',
                    UserWarning,
                    stacklevel=2,
                )

            description = get_func_description(func)
            parameters = get_func_parameters(func)

            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                try:
                    if inspect.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(func, *args, **kwargs)
                    return result
                except Exception as e:
                    return f"Error: {name}: {str(e)}"

            tool_definition = ToolDefinition(
                callable=wrapper,
                description=description,
                parameters=parameters,
                source_file_path=source_file_path,
                source_line_index=source_line_index,
            )
            self._tool_definitions[name] = tool_definition
            return wrapper

        return decorator

    def get_tools(
        api_format: Optional[ApiFormat] = None, strict: bool = False
    ) -> Union[List[Tuple[str, str, Dict[str, Any]]], Dict[str, Any]]:
        """
        Get tool information, optionally filtered by groups and formatted for specific API

        Args:
            groups: Optional list of groups to include. If None, includes all groups.
            api_format: Optional API format to convert to. If None, returns raw (name, description, parameters) tuple list.
                       Requires apiomorphic package for conversion.
            strict: Whether to enforce strict schema adherence in API formats that support it

        Returns:
            Either a list of (name, description, parameters) tuples (if api_format is None) or
            formatted schema for the specified API provider

        Raises:
            ImportError: If api_format is specified but apiomorphic package is not installed
        """
        # Collect raw tool information
        tools = []

        # Determine which groups to include
        if groups is None:
            relevant_groups = cls._tools.keys()
        else:
            relevant_groups = [g for g in groups if g in cls._tools]

        # Collect tools from relevant groups
        for group in relevant_groups:
            for name in cls._tools[group]:
                qualified_name = f"{group}.{name}"
                tools.append(
                    (
                        qualified_name,
                        cls._descriptions[qualified_name],
                        cls._parameters[qualified_name],
                    )
                )

        # Return raw tools if no format specified
        if api_format is None:
            return tools

        # Convert to requested format using apiomorphic
        if not APIOMORPHIC_AVAILABLE:
            raise ImportError(
                "apiomorphic package is required for API format conversion. "
                "Install it with: pip install apiomorphic"
            )

        return format_tool_schema(api_format, tools, strict=strict)

    @classmethod
    def _parse_tool_name(cls, name: str) -> Tuple[str, str]:
        """Parse a tool name into group and function name"""
        if "." in name:
            group, func_name = name.split(".", 1)
            return group, func_name
        else:
            # Search all groups for the function name
            for group, funcs in cls._tools.items():
                if name in funcs:
                    return group, name
        raise ValueError(f"Tool not found: {name}")

    @classmethod
    async def execute_async(cls, name: str, **kwargs) -> Any:
        """
        Execute a tool by name with given arguments asynchronsouly.
        Name can be either 'function_name' or 'group.function_name'

        Args:
            name: Name of the tool to execute (with optional group prefix)
            **kwargs: Arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        try:
            group, func_name = cls._parse_tool_name(name)
            if group in cls._tools and func_name in cls._tools[group]:
                if is_async_callable(func := cls._tools[group][func_name]):
                    return await func(**kwargs)
                else:
                    return func(**kwargs)
            return f"Error: Unknown tool '{name}'"
        except Exception as e:
            return f"Error: {str(e)}"

    @classmethod
    def execute_sync(cls, name: str, **kwargs) -> Any:
        """
        Execute a tool by name with given arguments synchronously.
        For sync functions, executes directly.
        For async functions, runs them in a new event loop.
        Name can be either 'function_name' or 'group.function_name'

        Args:
            name: Name of the tool to execute (with optional group prefix)
            **kwargs: Arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        try:
            group, func_name = cls._parse_tool_name(name)
            if group in cls._tools and func_name in cls._tools[group]:
                if is_async_callable(func := cls._tools[group][func_name]):
                    return asyncio.run(func(**kwargs))
                else:
                    return func(**kwargs)
            return f"Error: Unknown tool '{name}'"
        except Exception as e:
            return f"Error: {str(e)}"


def is_async_callable(obj: Any) -> bool:
    """Check if a callable is async."""
    return inspect.iscoroutinefunction(obj) or (
        hasattr(obj, "__call__") and inspect.iscoroutinefunction(obj.__call__)
    )
