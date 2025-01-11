# omnitoolbelt

A Python library for exposing groups of functions as tools to consumers such as Large Language Models (LLMs) or Discord users.

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

<!-- SPHINX-START -->

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/mmiguel6288/omnitoolbelt/workflows/CI/badge.svg
[actions-link]:             https://github.com/mmiguel6288/omnitoolbelt/actions
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/mmiguel6288/omnitoolbelt/discussions
<!-- prettier-ignore-end -->

## Features

- Simple decorator-based function registration
- Support for async and sync functions
- Automatic JSON schema generation from type hints
- Logical grouping of related tools
- Built-in support for OpenAI and Anthropic formats
- Support for both qualified and unqualified tool names
- Flexible sync and async execution options

## Installation

```bash
pip install llm-toolbelt
```

## Basic Usage

Here's a simple example of registering and using tools:

```python
from omnitoolbelt import Toolbelt

# Register some tools
@Toolbelt.tool(group="math")
async def add(a: float, b: float) -> float:
    """Add two numbers together"""
    return a + b

@Toolbelt.tool(group="text")
def uppercase(text: str) -> str:
    """Convert text to uppercase"""
    return text.upper()

# Get tool schemas for LLMs
tools = Toolbelt.get_tools()  # Get raw tool information
openai_tools = Toolbelt.get_tools(api_format="openai")  # Get OpenAI format
anthropic_tools = Toolbelt.get_tools(api_format="anthropic")  # Get Anthropic format

# Execute tools synchronously (great for scripts and interactive use)
result1 = Toolbelt.execute_sync("math.add", a=5, b=3)
result2 = Toolbelt.execute_sync("uppercase", text="hello")

# Execute tools asynchronously (great for async applications)
result3 = await Toolbelt.execute_async("math.add", a=5, b=3)
result4 = await Toolbelt.execute_async("uppercase", text="hello")
```

## Detailed Usage

### Tool Registration

Tools can be registered with optional group names:

```python
# Default group
@Toolbelt.tool()
def my_tool(): ...

# Named group
@Toolbelt.tool(group="utilities")
def another_tool(): ...
```

### Getting Tool Schemas

Get schemas in different formats:

```python
# Get raw tool information as (name, description, parameters) tuples
tools = Toolbelt.get_tools()

# Get tools for specific groups
math_tools = Toolbelt.get_tools(groups=["math"])

# Get OpenAI format with strict schema checking
openai_tools = Toolbelt.get_tools(api_format="openai", strict=True)

# Get Anthropic format
anthropic_tools = Toolbelt.get_tools(api_format="anthropic")
```

### Tool Execution

Tools can be executed both synchronously and asynchronously:

```python
# Synchronous execution (blocks until complete)
result1 = Toolbelt.execute_sync("math.add", a=5, b=3)
result2 = Toolbelt.execute_sync("uppercase", text="hello")

# Asynchronous execution
result3 = await Toolbelt.execute_async("math.add", a=5, b=3)
result4 = await Toolbelt.execute_async("uppercase", text="hello")

# Both methods support qualified and unqualified names
result5 = Toolbelt.execute_sync("add", a=5, b=3)  # Unqualified
result6 = await Toolbelt.execute_async("math.add", a=5, b=3)  # Qualified
```

### Concurrent Execution

The library supports concurrent execution in both sync and async contexts:

```python
# Synchronous concurrent execution
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(Toolbelt.execute_sync, "math.add", a=i, b=i)
        for i in range(5)
    ]
    results = [f.result() for f in futures]

# Asynchronous concurrent execution
import asyncio
tasks = [
    Toolbelt.execute_async("math.add", a=i, b=i)
    for i in range(5)]
results = await asyncio.gather(*tasks)
```

### Error Handling

Tool execution includes built-in error handling:

```python
# Synchronous error handling
result1 = Toolbelt.execute_sync("unknown_tool")  # Returns error message
result2 = Toolbelt.execute_sync("add", invalid_param=1)  # Returns error message

# Asynchronous error handling
result3 = await Toolbelt.execute_async("unknown_tool")
result4 = await Toolbelt.execute_async("add", invalid_param=1)
```

## API Format Support

The library supports multiple LLM API formats through the optional `apiomorphic` package:

```bash
pip install llm-toolbelt[api]  # Install with API format support
```

This enables automatic conversion to:
- OpenAI function calling format
- Anthropic tool format

## Type Hints

The library uses Python type hints to generate accurate JSON schemas:

```python
@Toolbelt.tool(group="example")
def process_data(
    text: str,
    count: int,
    enabled: bool = True,
    options: Dict[str, Any] = None
) -> List[str]:
    """
    Process some data with options
    """
    ...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
