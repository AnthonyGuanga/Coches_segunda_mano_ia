#!/usr/bin/env python3
"""
Test del flujo completo de extracción y búsqueda de recalls
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from tools_mcp import llm_extract_vehicle_info, check_vehicle_safety

async def test_full_flow():
    """Test del flujo completo desde texto hasta recalls"""
    print("🔄 Testing complete flow from text to recalls...")
    
    # Textos de prueba en español
    test_texts = [
        "Dime la seguridad de BMW Serie 3 2020",
        "¿Qué recalls tiene Toyota Corolla 2018?",
        "Ford F-150 2021 recalls",
        "Quiero saber sobre recalls de Chevrolet Malibu 2014"
    ]
    
    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"📝 Testing: '{text}'")
        print(f"{'='*60}")
        
        # Step 1: Extract vehicle info
        print("🧠 Step 1: Extracting vehicle information...")
        try:
            extract_result = await llm_extract_vehicle_info(text)
            print(f"Extract result: {extract_result}")
            
            if not extract_result.get("success"):
                print(f"❌ Extraction failed: {extract_result.get('error')}")
                continue
                
            data = extract_result.get("data", {})
            make = data.get("make")
            model = data.get("model")
            year = data.get("year")
            
            print(f"✅ Extracted: make='{make}', model='{model}', year={year}")
            
            if not make or not model:
                print("❌ Missing make or model")
                continue
            
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            continue
        
        # Step 2: Check vehicle safety
        print(f"\n🔍 Step 2: Checking safety for {make} {model} {year}...")
        try:
            safety_result = await check_vehicle_safety(make, model, year)
            print(f"Safety result keys: {list(safety_result.keys())}")
            
            if safety_result.get("success"):
                safety_data = safety_result.get("data", {})
                recalls = safety_data.get("recalls", [])
                print(f"✅ Found {len(recalls)} recalls")
                
                if len(recalls) > 0:
                    print("📋 Sample recalls:")
                    for i, recall in enumerate(recalls[:2], 1):
                        component = recall.get("component", "N/A")
                        summary = recall.get("summary", "N/A")[:100]
                        print(f"   {i}. {component}: {summary}...")
                else:
                    print("ℹ️  No recalls found for this specific vehicle")
            else:
                print(f"❌ Safety check failed: {safety_result.get('error')}")
                
        except Exception as e:
            print(f"❌ Safety check error: {e}")

async def test_problematic_cases():
    """Test casos específicos que están causando problemas"""
    print("\n🐛 Testing problematic cases...")
    
    # Test 1: BMW Serie 3 (el que está fallando)
    print("\n🔧 Test 1: BMW Serie 3 extraction...")
    result = await llm_extract_vehicle_info("Dime la seguridad de BMW Serie 3 2020")
    print(f"BMW extraction: {result}")
    
    if result.get("success"):
        data = result.get("data", {})
        make = data.get("make")
        model = data.get("model")
        year = data.get("year")
        
        print(f"Extracted values: make='{make}', model='{model}', year={year}")
        
        # Test different model variations for BMW
        model_variations = [
            "Serie 3", "3 Series", "3-Series", "3", "330i", "328i"
        ]
        
        print(f"\n🔍 Testing BMW model variations:")
        for test_model in model_variations:
            print(f"\n   Testing: BMW {test_model} 2020")
            try:
                safety_result = await check_vehicle_safety("BMW", test_model, 2020)
                if safety_result.get("success"):
                    recalls = safety_result.get("data", {}).get("recalls", [])
                    print(f"   ✅ {test_model}: {len(recalls)} recalls")
                else:
                    print(f"   ❌ {test_model}: {safety_result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   ❌ {test_model}: Exception - {e}")

async def main():
    """Función principal"""
    print("🚗 Complete Flow Testing")
    print("=" * 50)
    
    await test_problematic_cases()
    await test_full_flow()

if __name__ == "__main__":
    asyncio.run(main())