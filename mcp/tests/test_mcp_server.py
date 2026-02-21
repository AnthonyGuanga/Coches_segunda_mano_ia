"""
Tests para el servidor MCP y la integración FastAPI
Incluye tests de endpoints HTTP y stdio transport
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import httpx
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server import MCPServer, app

class TestMCPServer:
    """Tests para la clase MCPServer"""
    
    def test_server_initialization(self):
        """Test server initialization with tools"""
        server = MCPServer()
        
        assert server is not None
        assert hasattr(server, 'list_tools')
        assert hasattr(server, 'call_tool')
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test tool listing functionality"""
        server = MCPServer()
        result = await server.list_tools()
        
        assert "tools" in result
        tools = result["tools"]
        
        # Check that our expected tools are present
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "check_vehicle_safety",
            "llm_extract_vehicle_info", 
            "send_email_smtp",
            "generate_markdown_report",
            "web_fetch"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Check tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool calling"""
        
        with patch('tools.check_vehicle_safety') as mock_tool:
            mock_tool.return_value = {
                "success": True,
                "data": {"make": "BMW", "recalls": []}
            }
            
            server = MCPServer()
            result = await server.call_tool(
                "check_vehicle_safety",
                {"make": "BMW", "model": "Series 3"}
            )
            
            assert result is not None
            assert "content" in result
            mock_tool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown(self):
        """Test calling unknown tool"""
        server = MCPServer()
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("unknown_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_error_handling(self):
        """Test tool error handling"""
        
        with patch('tools.check_vehicle_safety') as mock_tool:
            mock_tool.side_effect = Exception("Tool execution failed")
            
            server = MCPServer()
            result = await server.call_tool(
                "check_vehicle_safety",
                {"make": "BMW"}
            )
            
            assert result is not None
            assert "content" in result
            assert "error" in str(result["content"]).lower()


class TestMCPFastAPIIntegration:
    """Tests para los endpoints FastAPI del servidor MCP"""
    
    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mcp_version" in data
    
    def test_list_tools_endpoint(self):
        """Test tools listing endpoint"""
        response = self.client.get(
            "/tools",
            headers={"Authorization": "Bearer default-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
    
    def test_list_tools_no_auth(self):
        """Test tools listing without authentication"""
        response = self.client.get("/tools")
        
        assert response.status_code == 401
    
    def test_list_tools_invalid_token(self):
        """Test tools listing with invalid token"""
        response = self.client.get(
            "/tools",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_call_tool_endpoint(self):
        """Test tool calling endpoint"""
        
        with patch('tools.generate_markdown_report') as mock_tool:
            mock_tool.return_value = {
                "success": True,
                "path": "/tmp/test.md",
                "filename": "test.md"
            }
            
            response = self.client.post(
                "/call-tool",
                json={
                    "name": "generate_markdown_report",
                    "arguments": {
                        "title": "Test Report",
                        "content": "Test content"
                    }
                },
                headers={"Authorization": "Bearer default-token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
    
    def test_call_tool_invalid_json(self):
        """Test tool calling with invalid JSON"""
        response = self.client.post(
            "/call-tool",
            data="invalid json",
            headers={
                "Authorization": "Bearer default-token",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 422
    
    def test_call_tool_missing_name(self):
        """Test tool calling without tool name"""
        response = self.client.post(
            "/call-tool",
            json={"arguments": {}},
            headers={"Authorization": "Bearer default-token"}
        )
        
        assert response.status_code == 422
    
    def test_server_sent_events_endpoint(self):
        """Test SSE endpoint structure"""
        # Note: Full SSE testing requires more complex setup
        # This tests the endpoint exists and requires auth
        
        response = self.client.get("/events")
        assert response.status_code == 401
        
        response = self.client.get(
            "/events",
            headers={"Authorization": "Bearer default-token"}
        )
        # SSE endpoints typically return 200 and stay open
        assert response.status_code == 200


class TestMCPStdioTransport:
    """Tests for MCP stdio transport functionality"""
    
    @pytest.mark.asyncio
    async def test_stdio_message_handling(self):
        """Test MCP stdio message format handling"""
        
        # Mock the stdio transport functionality
        server = MCPServer()
        
        # Simulate MCP JSON-RPC message for listing tools
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        # Test tools listing via stdio format
        tools_result = await server.list_tools()
        assert "tools" in tools_result
        
        # Simulate tool call message
        call_message = {
            "jsonrpc": "2.0", 
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "generate_markdown_report",
                "arguments": {"title": "Test", "content": "Content"}
            }
        }
        
        with patch('tools.generate_markdown_report') as mock_tool:
            mock_tool.return_value = {"success": True, "path": "/tmp/test.md"}
            
            result = await server.call_tool(
                call_message["params"]["name"],
                call_message["params"]["arguments"]
            )
            
            assert result is not None


class TestMCPAuthentication:
    """Tests for MCP authentication and authorization"""
    
    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)
    
    def test_valid_token_access(self):
        """Test access with valid token"""
        response = self.client.get(
            "/tools",
            headers={"Authorization": "Bearer default-token"}
        )
        
        assert response.status_code == 200
    
    def test_missing_authorization_header(self):
        """Test access without authorization header"""
        response = self.client.get("/tools")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_invalid_authorization_format(self):
        """Test invalid authorization header format"""
        response = self.client.get(
            "/tools",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == 401
    
    def test_invalid_token(self):
        """Test access with invalid token"""
        response = self.client.get(
            "/tools", 
            headers={"Authorization": "Bearer wrong-token"}
        )
        
        assert response.status_code == 401
    
    def test_environment_token_override(self):
        """Test token from environment variable"""
        
        with patch.dict('os.environ', {'MCP_TOKEN': 'env-token'}):
            # Need to reload app with new token
            from mcp_server import create_app
            test_app = create_app()
            test_client = TestClient(test_app)
            
            response = test_client.get(
                "/tools",
                headers={"Authorization": "Bearer env-token"}
            )
            
            assert response.status_code == 200


class TestMCPErrorHandling:
    """Tests for MCP error handling and edge cases"""
    
    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)
    
    def test_tool_execution_error(self):
        """Test handling of tool execution errors"""
        
        with patch('tools.check_vehicle_safety') as mock_tool:
            mock_tool.side_effect = Exception("External API failure")
            
            response = self.client.post(
                "/call-tool",
                json={
                    "name": "check_vehicle_safety",
                    "arguments": {"make": "BMW"}
                },
                headers={"Authorization": "Bearer default-token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            # Should contain error information but not crash
    
    def test_malformed_tool_arguments(self):
        """Test handling of malformed tool arguments"""
        
        response = self.client.post(
            "/call-tool",
            json={
                "name": "check_vehicle_safety",
                "arguments": "not-a-dict"
            },
            headers={"Authorization": "Bearer default-token"}
        )
        
        assert response.status_code == 422
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        
        response = self.client.options(
            "/tools",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Authorization": "Bearer default-token"
            }
        )
        
        # CORS should be handled by FastAPI middleware
        assert "access-control-allow-origin" in [
            h.lower() for h in response.headers.keys()
        ]


class TestMCPClientIntegration:
    """Integration tests for MCP client-server communication"""
    
    @pytest.mark.asyncio
    async def test_full_mcp_workflow_integration(self):
        """Test complete MCP workflow from client perspective"""
        
        # This would test the actual client-server MCP protocol
        # For now, test the server responses match MCP format
        
        server = MCPServer()
        
        # Test tools listing follows MCP format
        tools_response = await server.list_tools()
        assert "tools" in tools_response
        
        for tool in tools_response["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # Check schema format
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test asynchronous tool execution performance"""
        
        server = MCPServer()
        
        # Mock multiple tool calls
        with patch('tools.generate_markdown_report') as mock_tool:
            mock_tool.return_value = {"success": True, "path": "/tmp/test.md"}
            
            # Execute multiple tools concurrently
            tasks = []
            for i in range(5):
                task = server.call_tool(
                    "generate_markdown_report",
                    {"title": f"Report {i}", "content": f"Content {i}"}
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            for result in results:
                assert result is not None
                assert "content" in result


# Pytest fixtures and configuration
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mcp_server():
    """Provide MCP server instance for tests"""
    return MCPServer()

@pytest.fixture
def test_client():
    """Provide FastAPI test client"""
    return TestClient(app)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])