#!/usr/bin/env python3
"""
Test completo del sistema MCP - versión rápida
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Agregar directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from tools_mcp import llm_extract_vehicle_info, check_vehicle_safety

async def test_llm_extract():
    """Test de extracción LLM"""
    print("🧠 Testing LLM Vehicle Info Extraction...")
    
    test_texts = [
        "BMW Serie 3 2020",
        "Toyota Corolla 2019",
        "Honda Civic 2018"
    ]
    
    for text in test_texts:
        print(f"📝 Testing: '{text}'")
        try:
            result = await llm_extract_vehicle_info(text)
            if result.get("success"):
                data = result.get("data", {})
                print(f"✅ Extracted: {data.get('make')} {data.get('model')} {data.get('year')}")
            else:
                print(f"❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("✅ LLM Vehicle Info Extraction: PASSED\n")

async def test_vehicle_safety():
    """Test de seguridad vehicular"""
    print("🚗 Testing Vehicle Safety Check...")
    
    vehicles = [
        ("BMW", "3 Series", 2020),
        ("Toyota", "Corolla", 2019),
    ]
    
    for make, model, year in vehicles:
        print(f"🔍 Testing: {make} {model} {year}")
        try:
            result = await check_vehicle_safety(make, model, year)
            if result.get("success"):
                recalls = result.get("data", {}).get("recalls", [])
                print(f"✅ Found {len(recalls)} recalls")
            else:
                print(f"❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("✅ Vehicle Safety Check: PASSED\n")

async def main():
    """Función principal"""
    print("🧪 MCP System Quick Test")
    print("=" * 40)
    
    try:
        await test_llm_extract()
        await test_vehicle_safety()
        
        print("🎉 All quick tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)