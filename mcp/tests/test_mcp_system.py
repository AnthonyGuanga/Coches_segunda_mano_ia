#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las herramientas MCP funcionen correctamente
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import tools_mcp
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_llm_extract_vehicle_info():
    """Test LLM vehicle info extraction"""
    print("\n🧠 Testing LLM Vehicle Info Extraction...")
    
    try:
        from tools_mcp import llm_extract_vehicle_info
        
        test_texts = [
            "Quiero revisar la seguridad de BMW Serie 3 2020",
            "Toyota Corolla 2019 recalls check",
            "Honda Civic 2018 safety information",
            "Ford Focus 2021"
        ]
        
        for text in test_texts:
            print(f"\n📝 Testing text: '{text}'")
            result = await llm_extract_vehicle_info(text)
            
            if result.get("success"):
                data = result["data"]
                print(f"✅ Extracted: {data.get('make')} {data.get('model')} {data.get('year', 'N/A')}")
            else:
                print(f"❌ Failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing LLM extraction: {e}")
        return False

async def test_check_vehicle_safety():
    """Test vehicle safety checking with NHTSA API"""
    print("\n🚗 Testing Vehicle Safety Check...")
    
    try:
        from tools_mcp import check_vehicle_safety
        
        test_vehicles = [
            {"make": "BMW", "model": "3 Series", "year": 2020},
            {"make": "Toyota", "model": "Corolla", "year": 2019},
            {"make": "Honda", "model": "Civic", "year": 2018},
        ]
        
        for vehicle in test_vehicles:
            print(f"\n🔍 Testing: {vehicle['make']} {vehicle['model']} {vehicle['year']}")
            result = await check_vehicle_safety(
                make=vehicle["make"],
                model=vehicle["model"], 
                year=vehicle["year"]
            )
            
            if result.get("success"):
                data = result["data"]
                recalls = data.get("recalls", [])
                ratings = data.get("safety_ratings", {})
                print(f"✅ Found {len(recalls)} recalls")
                print(f"✅ Safety rating: {ratings.get('overall_rating', 'N/A')}")
            else:
                print(f"❌ Failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing vehicle safety check: {e}")
        return False

async def test_generate_markdown_report():
    """Test markdown report generation"""
    print("\n📄 Testing Markdown Report Generation...")
    
    try:
        from tools_mcp import generate_markdown_report
        
        title = "Test Vehicle Safety Report"
        content = """
# Vehicle Safety Analysis

## Test Vehicle: BMW 3 Series 2020

### Recalls Found
- No recalls found for this vehicle

### Safety Ratings
- Overall Rating: 5 stars
- Frontal Crash: 5 stars
- Side Crash: 5 stars

### Recommendations
- Excellent safety profile
- Recommended for purchase
"""
        
        result = await generate_markdown_report(
            title=title,
            content=content,
            metadata={"make": "BMW", "model": "3 Series", "year": 2020}
        )
        
        if result.get("success"):
            print(f"✅ Report generated: {result['filename']}")
            print(f"✅ Size: {result['size']} bytes")
            print(f"✅ Path: {result['path']}")
            
            # Verify file exists
            if Path(result['path']).exists():
                print("✅ File exists on disk")
                return True
            else:
                print("❌ File not found on disk")
                return False
        else:
            print(f"❌ Failed: {result.get('error')}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing report generation: {e}")
        return False

async def test_send_email_smtp():
    """Test email sending (simulation mode)"""
    print("\n📧 Testing Email Sending...")
    
    try:
        from tools_mcp import send_email_smtp
        
        result = await send_email_smtp(
            to_email="test@example.com",
            subject="Test Vehicle Safety Report",
            body="This is a test email from the MCP Vehicle Safety system.",
            attachment_path=None
        )
        
        if result.get("success"):
            print(f"✅ Email sent: {result['message']}")
            return True
        else:
            print(f"❌ Failed: {result.get('error')}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing email sending: {e}")
        return False

async def test_web_fetch():
    """Test web content fetching"""
    print("\n🌐 Testing Web Fetch...")
    
    try:
        from tools_mcp import web_fetch
        
        test_urls = [
            "https://httpbin.org/html",  # Simple test endpoint
            "https://www.nhtsa.gov",    # NHTSA website
        ]
        
        for url in test_urls:
            print(f"\n🔗 Testing URL: {url}")
            result = await web_fetch(url)
            
            if result.get("success"):
                data = result["data"]
                print(f"✅ Fetched {data['content_length']} characters")
                print(f"✅ Title: {data.get('title', 'N/A')[:50]}...")
            else:
                print(f"❌ Failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing web fetch: {e}")
        return False

async def test_mcp_tools_dict():
    """Test that all tools in mcp_tools_dict are callable"""
    print("\n🔧 Testing MCP Tools Dictionary...")
    
    try:
        from tools_mcp import mcp_tools_dict, mcp_tools_descriptions
        
        print(f"📋 Found {len(mcp_tools_dict)} tools:")
        for tool_name in mcp_tools_dict.keys():
            description = mcp_tools_descriptions.get(tool_name, "No description")
            print(f"  - {tool_name}: {description}")
        
        # Test that all tools are callable
        for tool_name, tool_func in mcp_tools_dict.items():
            if callable(tool_func):
                print(f"✅ {tool_name} is callable")
            else:
                print(f"❌ {tool_name} is not callable")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing tools dictionary: {e}")
        return False

async def test_environment_variables():
    """Test environment variables configuration"""
    print("\n⚙️ Testing Environment Variables...")
    
    env_vars = {
        "MCP_TOKEN": "default-token",
        "NHTSA_BASE_URL": "https://api.nhtsa.gov/SafetyRatings",
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "1025",
        "EMAIL_FROM": "vehicle-safety@mcp.local"
    }
    
    for var, default in env_vars.items():
        value = os.getenv(var, default)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: Not set (using default)")
    
    return True

async def run_all_tests():
    """Run all tests"""
    print("🧪 MCP Tools Testing Suite")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("MCP Tools Dictionary", test_mcp_tools_dict),
        ("LLM Vehicle Info Extraction", test_llm_extract_vehicle_info),
        ("Vehicle Safety Check (NHTSA API)", test_check_vehicle_safety),
        ("Markdown Report Generation", test_generate_markdown_report),
        ("Email Sending", test_send_email_smtp),
        ("Web Content Fetching", test_web_fetch),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
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
        print("🎉 All tests passed! The MCP system is working correctly.")
    else:
        print(f"⚠️ {total - passed} tests failed. Please check the errors above.")
    
    return passed == total

def main():
    """Main function"""
    try:
        result = asyncio.run(run_all_tests())
        if result:
            print("\n🚀 MCP system is ready for use!")
            sys.exit(0)
        else:
            print("\n🔧 Please fix the issues before using the MCP system.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Testing cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()