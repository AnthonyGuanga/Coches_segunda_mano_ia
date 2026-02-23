#!/usr/bin/env python3
"""
Script de prueba para verificar el comportamiento condicional del email
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "mcp"))

from mcp.agents.langgraph_adapter import VehicleSafetyAgent

async def test_email_behavior():
    """
    Prueba el comportamiento del email:
    1. Sin email - no debe enviar
    2. Con email - debe enviar
    """
    print("🔍 Iniciando prueba de comportamiento de email...")
    
    # Crear agente
    agent = VehicleSafetyAgent()
    
    # Test 1: SIN EMAIL - no debe enviar
    print("\n" + "="*60)
    print("📋 TEST 1: Consulta SIN email")
    print("="*60)
    
    result1 = await agent.run_analysis(
        user_input="BMW Serie 3 2020",
        email=""  # Sin email
    )
    
    print(f"✅ Análisis exitoso: {result1.get('success')}")
    print(f"📧 Email enviado: {result1.get('email_sent')}")
    print(f"📧 Estado email: {result1.get('email_status', 'N/A')}")
    
    # Test 2: CON EMAIL - debe enviar
    print("\n" + "="*60)
    print("📋 TEST 2: Consulta CON email")
    print("="*60)
    
    result2 = await agent.run_analysis(
        user_input="Honda Civic 2019",
        email="usuario@example.com"  # Con email
    )
    
    print(f"✅ Análisis exitoso: {result2.get('success')}")
    print(f"📧 Email enviado: {result2.get('email_sent')}")
    print(f"📧 Estado email: {result2.get('email_status', 'N/A')}")
    
    # Resumen
    print("\n" + "="*60)
    print("🎉 RESUMEN DE PRUEBAS")
    print("="*60)
    print(f"✅ Test 1 (sin email): Email enviado = {result1.get('email_sent')} (esperado: False)")
    print(f"✅ Test 2 (con email): Email enviado = {result2.get('email_sent')} (esperado: True)")
    
    if result1.get('email_sent') == False and result2.get('email_sent') == True:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
    else:
        print("❌ Algunas pruebas fallaron")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_email_behavior())