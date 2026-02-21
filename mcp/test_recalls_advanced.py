#!/usr/bin/env python3
"""
Test específico para verificar recalls conocidos
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from tools_mcp import check_vehicle_safety

async def test_known_recalls():
    """Probar vehículos que sabemos que tienen recalls"""
    print("🔍 Testing vehicles with known recalls...")
    
    # Vehículos que históricamente han tenido recalls
    test_vehicles = [
        # Ford tiene muchos recalls conocidos
        ("Ford", "F-150", 2021, "Popular truck with known issues"),
        ("Ford", "Explorer", 2020, "SUV with recent recalls"),
        ("Ford", "Escape", 2019, "Compact SUV"),
        
        # Toyota Takata airbag recalls
        ("Toyota", "Camry", 2015, "Takata airbag recalls"),
        ("Toyota", "Corolla", 2016, "Popular sedan"),
        
        # GM ignition switch recalls
        ("Chevrolet", "Malibu", 2014, "Ignition switch issues"),
        ("Chevrolet", "Cruze", 2015, "Compact car"),
        
        # Jeep recalls
        ("Jeep", "Grand Cherokee", 2018, "SUV recalls"),
        ("Jeep", "Wrangler", 2019, "Off-road vehicle"),
        
        # Nissan CVT issues
        ("Nissan", "Altima", 2018, "CVT transmission"),
        ("Nissan", "Sentra", 2017, "Compact car"),
    ]
    
    total_recalls_found = 0
    
    for make, model, year, description in test_vehicles:
        print(f"\n📋 Testing: {make} {model} {year} ({description})")
        
        try:
            result = await check_vehicle_safety(make, model, year)
            
            if result.get("success"):
                data = result.get("data", {})
                recalls = data.get("recalls", [])
                total_recalls_found += len(recalls)
                
                if len(recalls) > 0:
                    print(f"✅ Found {len(recalls)} recalls!")
                    for i, recall in enumerate(recalls[:2], 1):  # Show first 2
                        print(f"   {i}. {recall.get('component', 'N/A')}: {recall.get('summary', 'N/A')[:80]}...")
                else:
                    print(f"ℹ️  No recalls found for this vehicle")
                    
            else:
                print(f"❌ Error: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print(f"\n📊 SUMMARY:")
    print(f"Total vehicles tested: {len(test_vehicles)}")
    print(f"Total recalls found: {total_recalls_found}")
    
    if total_recalls_found == 0:
        print("⚠️  No recalls found for any vehicle. This might indicate:")
        print("   1. API endpoint changed")
        print("   2. API parameters incorrect")
        print("   3. These specific vehicles don't have recalls")
        print("   4. API is down or restricted")
    else:
        print(f"✅ System is working - found recalls!")

async def test_api_endpoints():
    """Test different API endpoints to understand structure"""
    print("\n🔧 Testing API endpoints...")
    
    import httpx
    
    base_urls = [
        "https://api.nhtsa.gov/SafetyRatings",
        "https://api.nhtsa.gov/recalls",
        "https://webapi.nhtsa.gov/api/Recalls"
    ]
    
    async with httpx.AsyncClient() as client:
        for base_url in base_urls:
            try:
                print(f"\n🌐 Testing: {base_url}")
                
                # Test basic connectivity
                response = await client.get(f"{base_url}/recalls/recallsByVehicle?make=Ford&model=F-150&modelYear=2021", timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", data.get("Results", []))
                    print(f"   Results found: {len(results)}")
                    
                    if len(results) > 0:
                        print(f"   ✅ This endpoint works!")
                        # Show structure
                        first_result = results[0]
                        print(f"   Sample keys: {list(first_result.keys())[:5]}")
                        break
                else:
                    print(f"   ❌ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")

async def main():
    """Función principal"""
    print("🚗 Advanced Recall Testing")
    print("=" * 50)
    
    await test_api_endpoints()
    await test_known_recalls()

if __name__ == "__main__":
    asyncio.run(main())