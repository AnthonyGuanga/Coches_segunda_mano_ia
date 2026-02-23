#!/bin/bash
# Script para probar el servidor MCP con diferentes clientes

echo "🔍 Testing Vehicle Safety MCP Server"
echo "===================================="

# Activar entorno virtual (desde mcp/)
source ../myenv/bin/activate

# Detener servidores existentes
echo "🧹 Cleaning up existing servers..."
pkill -f "mcp_server.py" 2>/dev/null || true
sleep 2

echo "📋 1. Testing stdio transport..."
timeout 3s python mcp_server.py --stdio > /dev/null 2>&1
if [ $? -eq 124 ]; then
    echo "✅ Stdio transport is working"
else
    echo "❌ Stdio transport failed"
fi

echo ""
echo "🌐 2. Testing HTTP transport..."

# Verificar que el puerto esté libre
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is busy, trying to free it..."
    lsof -ti:8000 | xargs -r kill 2>/dev/null
    sleep 2
fi

# Iniciar servidor HTTP
echo "Starting HTTP server..."
python mcp_server.py --http &
SERVER_PID=$!
sleep 5

# Verificar que el servidor esté funcionando
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start"
    exit 1
fi

echo "Server started with PID: $SERVER_PID"

# Test basic endpoints
echo ""
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Health endpoint OK: $HEALTH_RESPONSE"
else
    echo "❌ Health endpoint failed: $HEALTH_RESPONSE"
fi

echo ""
echo "Testing /tools endpoint..."
TOOLS_RESPONSE=$(curl -s -H "Authorization: Bearer default-token" http://localhost:8000/tools)
TOOLS_COUNT=$(echo "$TOOLS_RESPONSE" | grep -o '"name"' | wc -l)
if [ "$TOOLS_COUNT" -gt 0 ]; then
    echo "✅ Tools endpoint OK - Found $TOOLS_COUNT tools"
else
    echo "❌ Tools endpoint failed: $TOOLS_RESPONSE"
fi

echo ""
echo "Testing /stream endpoint..."
STREAM_RESPONSE=$(timeout 3s curl -s -N -H "Authorization: Bearer default-token" http://localhost:8000/stream | head -2)
if echo "$STREAM_RESPONSE" | grep -q "connected"; then
    echo "✅ Stream endpoint OK"
else
    echo "❌ Stream endpoint failed - Response: $STREAM_RESPONSE"
fi

echo ""
echo "Testing tool call..."
TOOL_CALL_DATA='{"name": "llm_extract_vehicle_info", "arguments": {"text": "BMW Serie 3 2020"}}'
TOOL_RESPONSE=$(curl -s -H "Authorization: Bearer default-token" -H "Content-Type: application/json" -X POST -d "$TOOL_CALL_DATA" http://localhost:8000/tools/call)
if echo "$TOOL_RESPONSE" | grep -q "success"; then
    echo "✅ Tool call OK"
else
    echo "❌ Tool call failed: $TOOL_RESPONSE"
fi

# Kill server
echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo ""
echo "📝 3. Configuration files created:"
echo "   - claude-config.json (for Claude Desktop)"
echo "   - vscode-mcp-config.json (for VS Code MCP extension)"

echo ""
echo "🎯 4. How to use:"
echo "   For Claude Desktop: Copy claude-config.json to Claude's config directory"
echo "   For VS Code: Install MCP extension and use vscode-mcp-config.json"
echo "   For HTTP clients: Connect to http://localhost:8000 with token 'default-token'"

echo ""
echo "✅ MCP Server testing completed!"