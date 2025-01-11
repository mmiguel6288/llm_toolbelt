from __future__ import annotations

import importlib.metadata

import omnitoolbelt as m

import pytest
from omnitoolbelt import Toolbelt, APIOMORPHIC_AVAILABLE
import asyncio


def test_version():
    assert importlib.metadata.version("omnitoolbelt") == m.__version__


# Sample tools for testing
@Toolbelt.tool(group="math")
async def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@Toolbelt.tool(group="math")
def multiply(x: float, y: float) -> float:
    """Multiply two numbers"""
    return x * y


@Toolbelt.tool(group="text")
async def uppercase(text: str) -> str:
    """Convert text to uppercase"""
    return text.upper()


@Toolbelt.tool()  # test default group
async def echo(message: str) -> str:
    """Echo a message back"""
    return message


# Helper to run async tests
async def async_test(coro):
    return await coro


def test_tool_registration():
    """Test that tools are properly registered"""
    # Check group registration
    assert "math" in Toolbelt._tools
    assert "text" in Toolbelt._tools
    assert "default" in Toolbelt._tools

    # Check function registration
    assert "add" in Toolbelt._tools["math"]
    assert "multiply" in Toolbelt._tools["math"]
    assert "uppercase" in Toolbelt._tools["text"]
    assert "echo" in Toolbelt._tools["default"]


def test_get_tools_no_format():
    """Test getting raw tool information"""
    tools = Toolbelt.get_tools()

    # Should return list of tuples
    assert isinstance(tools, list)
    assert all(isinstance(t, tuple) and len(t) == 3 for t in tools)

    # Check tool contents
    tool_names = [t[0] for t in tools]
    assert "math.add" in tool_names
    assert "math.multiply" in tool_names
    assert "text.uppercase" in tool_names
    assert "default.echo" in tool_names

    # Check parameter schemas
    add_tool = next(t for t in tools if t[0] == "math.add")
    assert add_tool[2]["properties"]["a"]["type"] == "number"
    assert add_tool[2]["properties"]["b"]["type"] == "number"
    assert set(add_tool[2]["required"]) == {"a", "b"}


def test_get_tools_filtered():
    """Test filtering tools by group"""
    math_tools = Toolbelt.get_tools(groups=["math"])
    text_tools = Toolbelt.get_tools(groups=["text"])

    math_names = [t[0] for t in math_tools]
    text_names = [t[0] for t in text_tools]

    assert all(name.startswith("math.") for name in math_names)
    assert all(name.startswith("text.") for name in text_names)
    assert len(math_tools) == 2
    assert len(text_tools) == 1


def test_group_qualified_names():
    """Test that group qualified names work correctly"""
    tools = Toolbelt.get_tools()

    # Check that all tools have group-qualified names
    for name, _, _ in tools:
        assert "." in name
        group, func = name.split(".")
        assert group in Toolbelt._tools
        assert func in Toolbelt._tools[group]


@pytest.mark.skipif(not APIOMORPHIC_AVAILABLE, reason="apiomorphic not installed")
def test_api_formats():
    """Test API format conversion (when apiomorphic is available)"""
    # OpenAI format
    openai_schema = Toolbelt.get_tools(api_format="openai")
    assert isinstance(openai_schema, list)
    for tool in openai_schema:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]

    # Anthropic format
    anthropic_schema = Toolbelt.get_tools(api_format="anthropic")
    assert isinstance(anthropic_schema, list)
    for tool in anthropic_schema:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


def test_type_conversion():
    """Test Python type to JSON schema type conversion"""
    assert Toolbelt._python_type_to_json(str) == "string"
    assert Toolbelt._python_type_to_json(int) == "integer"
    assert Toolbelt._python_type_to_json(float) == "number"
    assert Toolbelt._python_type_to_json(bool) == "boolean"
    assert Toolbelt._python_type_to_json(list) == "array"
    assert Toolbelt._python_type_to_json(dict) == "object"
    assert Toolbelt._python_type_to_json(complex) == "string"  # default fallback


@pytest.mark.asyncio
async def test_execute_async_with_async_tool():
    """Test executing async tools with execute_async"""
    result = await Toolbelt.execute_async("math.add", a=5, b=3)
    assert result == 8

    result = await Toolbelt.execute_async("text.uppercase", text="hello")
    assert result == "HELLO"


@pytest.mark.asyncio
async def test_execute_async_with_sync_tool():
    """Test executing sync tools with execute_async"""
    result = await Toolbelt.execute_async("math.multiply", x=4, y=6)
    assert result == 24


def test_execute_sync_with_async_tool():
    """Test executing async tools with execute_sync"""
    result = Toolbelt.execute_sync("math.add", a=5, b=3)
    assert result == 8

    result = Toolbelt.execute_sync("text.uppercase", text="hello")
    assert result == "HELLO"


def test_execute_sync_with_sync_tool():
    """Test executing sync tools with execute_sync"""
    result = Toolbelt.execute_sync("math.multiply", x=4, y=6)
    assert result == 24


@pytest.mark.asyncio
async def test_execute_async_errors():
    """Test error handling in execute_async"""
    # Unknown tool
    result = await Toolbelt.execute_async("unknown.tool")
    assert "Error" in result

    # Wrong parameters
    result = await Toolbelt.execute_async("math.add", wrong_param=1)
    assert "Error" in result


def test_execute_sync_errors():
    """Test error handling in execute_sync"""
    # Unknown tool
    result = Toolbelt.execute_sync("unknown.tool")
    assert "Error" in result

    # Wrong parameters
    result = Toolbelt.execute_sync("math.add", wrong_param=1)
    assert "Error" in result


def test_execute_sync_concurrent():
    """Test that execute_sync properly handles concurrent calls"""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(Toolbelt.execute_sync, "math.add", a=i, b=i)
            for i in range(5)
        ]
        results = [f.result() for f in futures]

    assert results == [0, 2, 4, 6, 8]


@pytest.mark.asyncio
async def test_execute_async_concurrent():
    """Test that execute_async properly handles concurrent calls"""
    tasks = [Toolbelt.execute_async("math.add", a=i, b=i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    assert results == [0, 2, 4, 6, 8]
