from typing import Any, Callable, Dict, Optional, List, Tuple, Union, get_type_hints
import inspect
from functools import wraps
import asyncio
from dataclasses import dataclass
try:
    from apiomorphic import ApiFormat, format_tool_schema
    APIOMORPHIC_AVAILABLE = True
except ImportError:
    APIOMORPHIC_AVAILABLE = False
    ApiFormat = Any

class Toolbelt:
    """Registry and executor for LLM-callable tools"""
    
    _tools: Dict[str, Dict[str, Callable]] = {}  # group -> {name -> function}
    _descriptions: Dict[str, str] = {}  # "group.name" -> docstring
    _parameters: Dict[str, Dict] = {}  # "group.name" -> parameter schema
    
    @classmethod
    def tool(cls, *, group: str = "default") -> Callable:
        """Register a function as an LLM-callable tool"""
        def decorator(func: Callable) -> Callable:
            name = func.__name__
            qualified_name = f"{group}.{name}"
            
            # Store function metadata
            if group not in cls._tools:
                cls._tools[group] = {}
            cls._tools[group][name] = func
            cls._descriptions[qualified_name] = func.__doc__ or ""
            
            # Generate parameter schema from type hints
            hints = get_type_hints(func)
            if "return" in hints:
                del hints["return"]
            
            cls._parameters[qualified_name] = {
                "type": "object",
                "properties": {
                    param: {"type": cls._python_type_to_json(typ)}
                    for param, typ in hints.items()
                },
                "required": list(hints.keys())
            }
            
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                try:
                    if inspect.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(func, *args, **kwargs)
                    return result
                except Exception as e:
                    return f"Error: {qualified_name}: {str(e)}"
                    
            return wrapper
        return decorator
    
    @classmethod
    def get_tools(
        cls, 
        groups: Optional[List[str]] = None,
        api_format: Optional[ApiFormat] = None,
        strict: bool = False
    ) -> Union[List[Tuple[str,str,Dict[str,Any]]], Dict[str, Any]]:
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
                tools.append((
                    qualified_name,
                    cls._descriptions[qualified_name],
                    cls._parameters[qualified_name],
                ))
        
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
        if '.' in name:
            group, func_name = name.split('.', 1)
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

    @staticmethod
    def _python_type_to_json(typ: Any) -> str:
        """Convert Python type to JSON schema type"""
        return {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }.get(typ, "string")
def is_async_callable(obj: Any) -> bool:
    """Check if a callable is async."""
    return (
            inspect.iscoroutinefunction(obj) or
            (hasattr(obj, '__call__') and
             inspect.iscoroutinefunction(obj.__call__))
            )
