#!/usr/bin/env python3
"""
MCP Server para Coches de Segunda Mano
Implementa transports stdio y streamablehttp con FastAPI
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        Tool,
        TextContent,
    )
except ImportError:
    print("Error: mcp library not installed. Install with: pip install mcp")
    sys.exit(1)

# Local imports
from tools_mcp import (
    check_vehicle_safety,
    generate_markdown_report,
    send_email_smtp,
    llm_extract_vehicle_info,
    mcp_tools_dict,
    mcp_tools_descriptions,
    format_mcp_tool_output
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp_server = Server("vehicle-safety-mcp")

# FastAPI app for HTTP transport
app = FastAPI(
    title="Vehicle Safety MCP Server",
    description="MCP Server for vehicle safety information and reports",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication
MCP_TOKEN = os.getenv("MCP_TOKEN", "default-token")

def verify_token(authorization: str = Header(None)) -> bool:
    """Verify MCP authentication token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if authorization != f"Bearer {MCP_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid token")
    
    return True

# Pydantic models for HTTP transport
class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ToolResponse(BaseModel):
    success: bool
    content: List[Dict[str, Any]]
    error: Optional[str] = None

# MCP Tool definitions
TOOLS = [
    Tool(
        name="check_vehicle_safety",
        description="Check vehicle safety information including recalls and safety ratings from NHTSA",
        inputSchema={
            "type": "object",
            "properties": {
                "make": {"type": "string", "description": "Vehicle manufacturer (e.g., BMW, Toyota)"},
                "model": {"type": "string", "description": "Vehicle model (e.g., Serie 3, Corolla)"},
                "year": {"type": "integer", "description": "Model year (optional)"},
                "vin": {"type": "string", "description": "Vehicle VIN (optional)"}
            },
            "required": ["make", "model"]
        }
    ),
    Tool(
        name="llm_extract_vehicle_info",
        description="Extract vehicle make, model, year from natural language text using LLM",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Natural language text containing vehicle information"}
            },
            "required": ["text"]
        }
    ),
    Tool(
        name="generate_markdown_report",
        description="Generate a markdown report file",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Report title"},
                "content": {"type": "string", "description": "Report content in markdown format"},
                "filename": {"type": "string", "description": "Output filename (optional)"}
            },
            "required": ["title", "content"]
        }
    ),
    Tool(
        name="send_email_smtp",
        description="Send email via SMTP (real or simulated)",
        inputSchema={
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
                "simulate": {"type": "boolean", "description": "Force simulation mode (default: auto)"}
            },
            "required": ["recipient", "subject", "body"]
        }
    )
]

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools"""
    return TOOLS

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call an MCP tool with given arguments"""
    logger.info(f"Calling tool: {name} with args: {_sanitize_args(arguments)}")
    
    try:
        if name == "check_vehicle_safety":
            result = await check_vehicle_safety(
                make=arguments["make"],
                model=arguments["model"],
                year=arguments.get("year"),
                vin=arguments.get("vin")
            )
        elif name == "llm_extract_vehicle_info":
            result = await llm_extract_vehicle_info(arguments["text"])
        elif name == "generate_markdown_report":
            result = await generate_markdown_report(
                title=arguments["title"],
                content=arguments["content"],
                metadata=arguments.get("metadata")
            )
        elif name == "send_email_smtp":
            result = await send_email_smtp(
                to_email=arguments["recipient"],  # Usar recipient del schema
                subject=arguments["subject"],
                body=arguments["body"],
                attachment_path=arguments.get("attachment_path")
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # Format result as TextContent
        content_text = json.dumps(result, indent=2, ensure_ascii=False)
        return [TextContent(type="text", text=content_text)]
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        error_result = {"success": False, "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

def _sanitize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize arguments for logging (hide sensitive data)"""
    sanitized = dict(args)
    # Hide VIN for privacy
    if "vin" in sanitized and sanitized["vin"]:
        sanitized["vin"] = sanitized["vin"][:4] + "***"
    # Hide email addresses
    if "recipient" in sanitized:
        email = sanitized["recipient"]
        if "@" in email:
            local, domain = email.split("@", 1)
            sanitized["recipient"] = f"{local[:2]}***@{domain}"
    return sanitized

# FastAPI endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "vehicle-safety-mcp", "version": "1.0.0"}

@app.get("/tools")
async def list_tools_http(authenticated: bool = Depends(verify_token)):
    """List available tools via HTTP"""
    return {"tools": [tool.model_dump() for tool in TOOLS]}

@app.post("/tools/call")
async def call_tool_http(
    tool_call: ToolCall,
    authenticated: bool = Depends(verify_token)
) -> ToolResponse:
    """Call a tool via HTTP"""
    try:
        result = await call_tool(tool_call.name, tool_call.arguments)
        return ToolResponse(
            success=True,
            content=[{"type": content.type, "text": content.text} for content in result]
        )
    except Exception as e:
        logger.error(f"HTTP tool call error: {e}")
        return ToolResponse(
            success=False,
            content=[],
            error=str(e)
        )

# Alias endpoint for compatibility
@app.post("/call-tool")
async def call_tool_alias(
    tool_call: ToolCall,
    authenticated: bool = Depends(verify_token)
) -> ToolResponse:
    """Call a tool via HTTP (alias endpoint)"""
    return await call_tool_http(tool_call, authenticated)

@app.get("/tools/call/{tool_name}")
async def call_tool_get(
    tool_name: str,
    authenticated: bool = Depends(verify_token),
    **params
):
    """Call tool via GET (for simple calls)"""
    try:
        result = await call_tool(tool_name, dict(params))
        return {
            "success": True,
            "result": [{"type": content.type, "text": content.text} for content in result]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Server-Sent Events endpoint for streaming
@app.get("/stream")
async def stream_events(authenticated: bool = Depends(verify_token)):
    """Stream MCP events via Server-Sent Events"""
    
    async def event_stream():
        # Send initial connection event with proper SSE format
        yield "event: connected\n"
        yield f"data: {json.dumps({'type': 'connected', 'server': 'vehicle-safety-mcp', 'timestamp': str(datetime.now())})}\n\n"
        
        # Send server info immediately  
        yield "event: server_info\n"
        yield f"data: {json.dumps({'type': 'server_info', 'tools_count': len(TOOLS), 'version': '1.0.0'})}\n\n"
        
        # Keep connection alive with periodic pings
        counter = 0
        while True:
            await asyncio.sleep(30)  # Ping every 30 seconds
            counter += 1
            yield "event: ping\n"
            yield f"data: {json.dumps({'type': 'ping', 'count': counter, 'timestamp': str(datetime.now())})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time MCP communication"""
    await websocket.accept()
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "server": "vehicle-safety-mcp",
            "version": "1.0.0",
            "available_tools": [tool.name for tool in TOOLS]
        }))
        
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            try:
                request = json.loads(data)
                
                if request.get("type") == "call_tool":
                    tool_name = request.get("name")
                    arguments = request.get("arguments", {})
                    
                    # Call the tool
                    result = await call_tool(tool_name, arguments)
                    
                    # Send response
                    response = {
                        "type": "tool_result",
                        "success": True,
                        "result": [{"type": content.type, "text": content.text} for content in result]
                    }
                    await websocket.send_text(json.dumps(response))
                    
                elif request.get("type") == "list_tools":
                    response = {
                        "type": "tools_list",
                        "tools": [tool.model_dump() for tool in TOOLS]
                    }
                    await websocket.send_text(json.dumps(response))
                    
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Unknown request type: {request.get('type')}"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON format"
                }))
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

async def run_stdio():
    """Run MCP server with stdio transport"""
    logger.info("Starting MCP server with stdio transport...")
    
    try:
        # Import all tools functions
        from tools_mcp import (
            check_vehicle_safety,
            llm_extract_vehicle_info, 
            generate_markdown_report,
            send_email_smtp
        )
        
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error in stdio server: {e}")
        import traceback
        traceback.print_exc()
        raise

def run_http(host: str = "0.0.0.0", port: int = 8000):
    """Run MCP server with HTTP transport"""
    logger.info(f"Starting MCP server with HTTP transport on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Vehicle Safety MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run with stdio transport")
    parser.add_argument("--http", action="store_true", help="Run with HTTP transport")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    
    args = parser.parse_args()
    
    if args.stdio:
        asyncio.run(run_stdio())
    elif args.http:
        run_http(args.host, args.port)
    else:
        print("Please specify --stdio or --http transport")
        print("Examples:")
        print("  python mcp_server.py --stdio")
        print("  python mcp_server.py --http --port 8000")
        sys.exit(1)

if __name__ == "__main__":
    main()