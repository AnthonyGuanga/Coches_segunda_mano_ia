#!/usr/bin/env python3
"""
Script de prueba para los endpoints HTTP del servidor MCP
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPServerTester:
    def __init__(self, base_url: str = "http://localhost:8000", token: str = "default-token"):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("🏥 Testing Health Check...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Health check passed: {data.get('status')}")
                    print(f"✅ MCP Version: {data.get('mcp_version', 'N/A')}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_list_tools(self) -> bool:
        """Test tools listing endpoint"""
        print("\n🔧 Testing Tools Listing...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/tools", headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    tools = data.get("tools", [])
                    print(f"✅ Found {len(tools)} tools:")
                    
                    for tool in tools:
                        name = tool.get("name")
                        desc = tool.get("description", "No description")
                        print(f"   - {name}: {desc[:60]}...")
                    
                    return True
                else:
                    print(f"❌ Tools listing failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Tools listing error: {e}")
            return False
    
    async def test_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Test calling a specific tool"""
        print(f"\n⚙️ Testing Tool: {tool_name}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "name": tool_name,
                    "arguments": arguments
                }
                
                response = await client.post(
                    f"{self.base_url}/call-tool", 
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Tool {tool_name} executed successfully")
                    
                    # Try to extract meaningful info from response
                    content = data.get("content", [])
                    if content and isinstance(content, list) and len(content) > 0:
                        text = content[0].get("text", "")
                        print(f"✅ Response preview: {text[:100]}...")
                    
                    return True
                else:
                    print(f"❌ Tool {tool_name} failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Raw error: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Tool {tool_name} error: {e}")
            return False
    
    async def test_authentication(self) -> bool:
        """Test authentication with wrong token"""
        print("\n🔐 Testing Authentication...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test without token
                response = await client.get(f"{self.base_url}/tools")
                if response.status_code == 401:
                    print("✅ Correctly rejected request without token")
                else:
                    print(f"❌ Should have rejected request without token: {response.status_code}")
                    return False
                
                # Test with wrong token
                wrong_headers = {"Authorization": "Bearer wrong-token"}
                response = await client.get(f"{self.base_url}/tools", headers=wrong_headers)
                if response.status_code == 401:
                    print("✅ Correctly rejected request with wrong token")
                    return True
                else:
                    print(f"❌ Should have rejected request with wrong token: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all MCP server tests"""
        print("🧪 MCP Server Testing Suite")
        print("=" * 50)
        
        # Check if server is running
        print("🔍 Checking if MCP server is running...")
        server_running = await self.test_health_check()
        
        if not server_running:
            print("\n❌ MCP server is not running!")
            print("Please start the server with:")
            print("   python mcp_server.py --http")
            return False
        
        # Run tests
        tests = [
            ("Authentication", self.test_authentication),
            ("Tools Listing", self.test_list_tools),
        ]
        
        # Add tool-specific tests
        tool_tests = [
            ("llm_extract_vehicle_info", {"text": "BMW Serie 3 2020 safety check"}),
            ("generate_markdown_report", {
                "title": "Test Report",
                "content": "# Test\n\nThis is a test report."
            }),
            ("send_email_smtp", {
                "to_email": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email."
            }),
        ]
        
        results = {}
        
        # Run basic tests
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results[test_name] = False
        
        # Run tool tests
        for tool_name, arguments in tool_tests:
            test_name = f"Tool: {tool_name}"
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = await self.test_call_tool(tool_name, arguments)
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results[test_name] = False
        
        # Summary
        print(f"\n{'='*50}")
        print("🎯 TEST SUMMARY")
        print(f"{'='*50}")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
        
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All MCP server tests passed!")
        else:
            print(f"⚠️ {total - passed} tests failed. Please check the errors above.")
        
        return passed == total

async def main():
    """Main function"""
    tester = MCPServerTester()
    
    try:
        success = await tester.run_all_tests()
        if success:
            print("\n🚀 MCP server is working correctly!")
            
            # Test some additional endpoints
            print("\n🌐 Testing additional endpoints...")
            print("Try these URLs in your browser:")
            print("  - http://localhost:8000/health")
            print("  - http://localhost:8000/docs (FastAPI docs)")
            
        return success
        
    except KeyboardInterrupt:
        print("\n👋 Testing cancelled by user.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)