#!/usr/bin/env python3
"""
Ejemplo de uso rápido del sistema MCP de análisis vehicular
Demuestra el workflow completo desde extracción hasta reporte
"""

import asyncio
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_mcp_tools():
    """Demonstrate individual MCP tools"""
    
    print("🔧 Demo: Herramientas MCP Individuales")
    print("=" * 50)
    
    # Import MCP tools
    try:
        from tools_mcp import (
            llm_extract_vehicle_info,
            check_vehicle_safety, 
            generate_markdown_report,
            send_email_smtp
        )
    except ImportError as e:
        print(f"❌ Error importing tools: {e}")
        return
    
    # 1. Extract vehicle info from text
    print("\n1️⃣ Extracción de información vehicular con LLM...")
    user_query = "Quiero revisar la seguridad de mi BMW Serie 3 del año 2020"
    
    extract_result = await llm_extract_vehicle_info(user_query)
    if extract_result["success"]:
        vehicle_info = extract_result["data"]
        print(f"✅ Información extraída:")
        print(f"   - Marca: {vehicle_info.get('make')}")
        print(f"   - Modelo: {vehicle_info.get('model')}")
        print(f"   - Año: {vehicle_info.get('year')}")
    else:
        print(f"❌ Error: {extract_result['error']}")
        return
    
    # 2. Check vehicle safety
    print("\n2️⃣ Consulta de seguridad vehicular (NHTSA)...")
    
    safety_result = await check_vehicle_safety(
        make=vehicle_info["make"],
        model=vehicle_info["model"],
        year=vehicle_info["year"]
    )
    
    if safety_result["success"]:
        safety_data = safety_result["data"]
        recalls = safety_data.get("recalls", [])
        ratings = safety_data.get("safety_ratings", {})
        
        print(f"✅ Datos de seguridad obtenidos:")
        print(f"   - Recalls encontrados: {len(recalls)}")
        print(f"   - Calificación general: {ratings.get('overall_rating', 'N/A')}")
        
        if recalls:
            print(f"   - Primer recall: {recalls[0].get('summary', 'N/A')[:50]}...")
    else:
        print(f"❌ Error: {safety_result['error']}")
        return
    
    # 3. Generate report
    print("\n3️⃣ Generación de reporte Markdown...")
    
    report_content = f"""
# Reporte de Seguridad: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}

## Resumen
- **Vehículo**: {vehicle_info['make']} {vehicle_info['model']} ({vehicle_info['year']})
- **Recalls encontrados**: {len(recalls)}
- **Calificación NHTSA**: {ratings.get('overall_rating', 'No disponible')}

## Detalles de Seguridad
"""
    
    if recalls:
        report_content += "\n### Recalls Activos\n"
        for i, recall in enumerate(recalls[:3], 1):  # Show first 3
            report_content += f"\n**{i}. {recall.get('component', 'N/A')}**\n"
            report_content += f"- Campaña: {recall.get('campaign_number', 'N/A')}\n"
            report_content += f"- Resumen: {recall.get('summary', 'N/A')}\n"
    else:
        report_content += "\n✅ No se encontraron recalls activos para este vehículo.\n"
    
    if ratings:
        report_content += "\n### Calificaciones de Seguridad\n"
        report_content += f"- **General**: {ratings.get('overall_rating', 'N/A')} estrellas\n"
        report_content += f"- **Choque frontal**: {ratings.get('frontal_crash', 'N/A')}\n"
        report_content += f"- **Choque lateral**: {ratings.get('side_crash', 'N/A')}\n"
    
    report_result = await generate_markdown_report(
        title=f"Seguridad_{vehicle_info['make']}_{vehicle_info['model']}_{vehicle_info['year']}_Report",
        content=report_content
    )
    
    if report_result["success"]:
        print(f"✅ Reporte generado: {report_result['path']}")
        print(f"   - Tamaño: {report_result.get('size', 'N/A')} bytes")
    else:
        print(f"❌ Error: {report_result['error']}")
        return
    
    # 4. Send notification email (simulated)
    print("\n4️⃣ Envío de notificación por email...")
    
    email_result = await send_email_smtp(
        to_email="usuario@example.com",
        subject=f"Reporte de Seguridad: {vehicle_info['make']} {vehicle_info['model']}",
        body=f"Se ha generado el reporte de seguridad para su vehículo.\n\nResumen:\n- Recalls: {len(recalls)}\n- Calificación: {ratings.get('overall_rating', 'N/A')}",
        attachment_path=report_result["path"]
    )
    
    if email_result["success"]:
        print(f"✅ Email enviado: {email_result['message']}")
    else:
        print(f"❌ Error: {email_result['error']}")
    
    print(f"\n🎉 Demo completado exitosamente!")
    print(f"📄 Reporte disponible en: {report_result['path']}")

async def demo_langgraph_agent():
    """Demonstrate LangGraph agent workflow"""
    
    print("\n🤖 Demo: Agente LangGraph Completo")
    print("=" * 50)
    
    try:
        from agents.langgraph_adapter import VehicleSafetyAgent
        
        # Initialize agent (assuming MCP server is running)
        agent = VehicleSafetyAgent(
            mcp_base_url="http://localhost:8000",
            mcp_token="default-token"
        )
        
        print("\n🚀 Ejecutando análisis completo con agente...")
        
        # Run complete analysis
        user_input = "Necesito verificar la seguridad de un Toyota Corolla 2019 que estoy considerando comprar"
        
        result = await agent.run_analysis(user_input)
        
        if result.get("success"):
            print("✅ Análisis completado por el agente:")
            print(f"   - Vehículo procesado: {result.get('extracted_info', {})}")
            print(f"   - Reporte generado: {result.get('markdown_path')}")
            print(f"   - Email enviado: {result.get('email_sent')}")
        else:
            print(f"❌ Error del agente: {result.get('error')}")
        
        await agent.close()
        
    except ImportError:
        print("⚠️ LangGraph agent no disponible (dependencias opcionales)")
    except Exception as e:
        print(f"❌ Error ejecutando agente: {e}")

async def demo_mcp_client():
    """Demonstrate MCP client usage"""
    
    print("\n📡 Demo: Cliente MCP HTTP")
    print("=" * 50)
    
    try:
        from agents.langgraph_adapter import MCPClient
        
        client = MCPClient(
            base_url="http://localhost:8000",
            token="default-token"
        )
        
        print("\n1️⃣ Listando herramientas disponibles...")
        
        try:
            tools = await client.list_tools()
            print(f"✅ Herramientas encontradas: {len(tools)}")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:50]}...")
        except Exception as e:
            print(f"❌ No se pudo conectar al servidor MCP: {e}")
            print("   Asegúrate de que el servidor MCP esté ejecutándose:")
            print("   python mcp_server.py --http")
            return
        
        print("\n2️⃣ Ejecutando herramienta via cliente MCP...")
        
        # Test tool execution
        result = await client.call_tool(
            "llm_extract_vehicle_info",
            {"text": "Honda Civic 2018 revisión de seguridad"}
        )
        
        if result.get("success"):
            print("✅ Herramienta ejecutada exitosamente:")
            print(f"   - Resultado: {result.get('data')}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        await client.close()
        
    except ImportError:
        print("⚠️ Cliente MCP no disponible")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_environment():
    """Check if environment is properly configured"""
    
    print("🔍 Verificando configuración del entorno...")
    
    issues = []
    
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ requerido")
    else:
        print(f"✅ Python {sys.version.split()[0]}")
    
    # Check required files
    required_files = ["tools.py", "mcp_server.py"]
    for file in required_files:
        if not Path(file).exists():
            issues.append(f"Archivo faltante: {file}")
        else:
            print(f"✅ {file}")
    
    # Check optional dependencies
    optional_deps = {
        "gradio": "pip install gradio",
        "google.generativeai": "pip install google-generativeai",
        "mcp": "pip install mcp"
    }
    
    for module, install_cmd in optional_deps.items():
        try:
            __import__(module.replace(".", "/"))
            print(f"✅ {module}")
        except ImportError:
            print(f"⚠️ {module} (opcional): {install_cmd}")
    
    # Check environment variables
    env_vars = {
        "MCP_TOKEN": "default-token",
        "NHTSA_BASE_URL": "https://api.nhtsa.gov/SafetyRatings"
    }
    
    for var, default in env_vars.items():
        value = os.getenv(var, default)
        if value:
            print(f"✅ {var}: {value[:20]}...")
        else:
            print(f"⚠️ {var} no configurado")
    
    if issues:
        print(f"\n❌ Problemas encontrados:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print(f"\n✅ Entorno configurado correctamente")
    return True

async def main():
    """Main demo function"""
    
    print("🚗 MCP Vehicle Safety Analysis System - Demo")
    print("=" * 60)
    
    # Check environment first
    if not check_environment():
        print("\n⚠️ Por favor, resuelve los problemas de configuración antes de continuar.")
        return
    
    print("\n🎯 Selecciona el tipo de demo:")
    print("1. Herramientas MCP individuales (no requiere servidor)")
    print("2. Agente LangGraph completo")
    print("3. Cliente MCP HTTP (requiere servidor ejecutándose)")
    print("4. Todos los demos")
    
    try:
        choice = input("\nIngresa tu opción (1-4): ").strip()
        
        if choice == "1" or choice == "4":
            await demo_mcp_tools()
        
        if choice == "2" or choice == "4":
            await demo_langgraph_agent()
        
        if choice == "3" or choice == "4":
            await demo_mcp_client()
        
        if choice not in ["1", "2", "3", "4"]:
            print("❌ Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
    
    print(f"\n📚 Para más información, consulta el README.md")

if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())