"""
Minimal desktop automation MCP server.
Tools: screenshot, click, type_text, get_window_title
"""
import base64
import io
import subprocess
import sys

import pyautogui
from PIL import ImageGrab
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

pyautogui.FAILSAFE = False

app = Server("desktop")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="screenshot",
            description="Capture the full screen and return it as a base64 PNG.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="click",
            description="Left-click at screen coordinates (x, y).",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
            },
        ),
        types.Tool(
            name="double_click",
            description="Double-click at screen coordinates (x, y).",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
                "required": ["x", "y"],
            },
        ),
        types.Tool(
            name="type_text",
            description="Type text at the current cursor position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="key",
            description="Press a keyboard key (e.g. 'enter', 'tab', 'escape').",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name"},
                },
                "required": ["key"],
            },
        ),
        types.Tool(
            name="run_python",
            description="Run a Python command in the project and return stdout.",
            inputSchema={
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments after 'python', e.g. ['tests/test_notes.py']",
                    }
                },
                "required": ["args"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
    if name == "screenshot":
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode()
        return [types.ImageContent(type="image", data=data, mimeType="image/png")]

    if name == "click":
        pyautogui.click(arguments["x"], arguments["y"])
        return [types.TextContent(type="text", text=f"Clicked ({arguments['x']}, {arguments['y']})")]

    if name == "double_click":
        pyautogui.doubleClick(arguments["x"], arguments["y"])
        return [types.TextContent(type="text", text=f"Double-clicked ({arguments['x']}, {arguments['y']})")]

    if name == "type_text":
        pyautogui.write(arguments["text"], interval=0.02)
        return [types.TextContent(type="text", text=f"Typed: {arguments['text']}")]

    if name == "key":
        pyautogui.press(arguments["key"])
        return [types.TextContent(type="text", text=f"Pressed: {arguments['key']}")]

    if name == "run_python":
        result = subprocess.run(
            [sys.executable] + arguments["args"],
            capture_output=True, text=True, timeout=60,
            cwd=r"C:\Users\Abesh\Desktop\ClaudeCodeApparel\ClaudeCode",
        )
        output = result.stdout + result.stderr
        return [types.TextContent(type="text", text=output or "(no output)")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(_main())
