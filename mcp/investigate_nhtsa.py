#!/usr/bin/env python3
"""
Investigación de la API de NHTSA actualizada
"""

import asyncio
import httpx

async def investigate_nhtsa_api():
    """Investigar la estructura actual de la API de NHTSA"""
    print("🔍 Investigating NHTSA API structure...")
    
    # URLs conocidas de NHTSA
    test_urls = [
        "https://webapi.nhtsa.gov/api/Recalls/vehicle/modelyear/2021/make/ford/model/f-150",
        "https://webapi.nhtsa.gov/api/Recalls/vehicle/modelyear/2020/make/toyota/model/corolla", 
        "https://api.nhtsa.gov/recalls/recallsByVehicle?make=Ford&model=F-150&modelYear=2021",
        "https://api.nhtsa.gov/products/vehicle/recalls?make=Ford&model=F-150&modelYear=2021",
        "https://webapi.nhtsa.gov/api/Recalls?make=Ford&model=F-150&modelYear=2021",
        "https://one.nhtsa.gov/webapi/api/Recalls/vehicle/modelyear/2021/make/ford/model/f-150"
    ]
    
    async with httpx.AsyncClient() as client:
        for url in test_urls:
            print(f"\n🌐 Testing: {url}")
            try:
                response = await client.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Try different possible result keys
                        results = None
                        result_keys = ["results", "Results", "recalls", "Recalls", "Count", "count"]
                        
                        for key in result_keys:
                            if key in data:
                                if isinstance(data[key], list):
                                    results = data[key]
                                    print(f"   ✅ Found results under key '{key}': {len(results)} items")
                                    break
                                elif isinstance(data[key], int):
                                    print(f"   📊 Count under key '{key}': {data[key]}")
                        
                        if results is None:
                            print(f"   📋 Response keys: {list(data.keys())}")
                            if data:
                                # Show first few items if it's a dict
                                for key, value in list(data.items())[:3]:
                                    print(f"      {key}: {type(value)} - {str(value)[:50]}...")
                        
                        if results and len(results) > 0:
                            print(f"   🎉 SUCCESS! Found {len(results)} recalls")
                            first_recall = results[0]
                            print(f"   📄 Sample recall keys: {list(first_recall.keys())[:5]}")
                            return url, results  # Return successful URL and data
                            
                    except Exception as e:
                        print(f"   ❌ JSON parse error: {e}")
                        print(f"   📄 Raw response: {response.text[:200]}...")
                        
                else:
                    print(f"   ❌ HTTP {response.status_code}")
                    if response.status_code == 403:
                        print("   🚫 Access denied - API might require authentication")
                    elif response.status_code == 404:
                        print("   🔍 Endpoint not found")
                        
            except Exception as e:
                print(f"   💥 Request failed: {e}")
    
    print("\n❌ No working API endpoint found")
    return None, None

async def test_alternative_sources():
    """Test alternative data sources"""
    print("\n🔄 Testing alternative recall sources...")
    
    alternative_urls = [
        "https://www.safercar.gov/api/v1/recalls?make=Ford&model=F-150&year=2021",
        "https://recalls-api.safercar.gov/recalls?make=Ford&model=F-150&year=2021",
    ]
    
    async with httpx.AsyncClient() as client:
        for url in alternative_urls:
            print(f"\n🌐 Testing alternative: {url}")
            try:
                response = await client.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   📋 Keys: {list(data.keys())}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")

async def main():
    print("🚗 NHTSA API Investigation")
    print("=" * 40)
    
    working_url, sample_data = await investigate_nhtsa_api()
    
    if working_url:
        print(f"\n✅ FOUND WORKING API: {working_url}")
        print("🔧 Updating tools_mcp.py with correct endpoint...")
    else:
        print("\n⚠️ No working NHTSA API found")
        print("📝 Recommendations:")
        print("   1. Use mock data for demonstration")
        print("   2. Find alternative recall databases")
        print("   3. Implement web scraping fallback")
        
        await test_alternative_sources()

if __name__ == "__main__":
    asyncio.run(main())