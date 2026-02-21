#!/usr/bin/env python3
"""
🚗 MCP Vehicle System - Command Line Interface
Script principal para gestionar el sistema MCP completo
"""

import argparse
import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """Print MCP system banner"""
    print("""
🚗 MCP Vehicle Safety Analysis System
====================================
Sistema completo con Model Context Protocol
    """)

def run_command(command, description):
    """Run a system command with description"""
    print(f"🔧 {description}...")
    print(f"💻 Ejecutando: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print(f"✅ {description} completado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️ {description} cancelado por el usuario")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="MCP Vehicle System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python mcp_cli.py --test           # Ejecutar todas las pruebas
  python mcp_cli.py --server         # Iniciar servidor HTTP
  python mcp_cli.py --ui             # Iniciar interfaz web
  python mcp_cli.py --demo           # Ejecutar demostración
  python mcp_cli.py --test-endpoints # Probar endpoints HTTP
  python mcp_cli.py --help-setup     # Ayuda para configuración
        """
    )
    
    parser.add_argument('--test', action='store_true',
                       help='Ejecutar suite completa de pruebas del sistema')
    parser.add_argument('--server', action='store_true',
                       help='Iniciar servidor MCP en modo HTTP')
    parser.add_argument('--ui', action='store_true',
                       help='Iniciar interfaz web Gradio')
    parser.add_argument('--demo', action='store_true',
                       help='Ejecutar script de demostración')
    parser.add_argument('--test-endpoints', action='store_true',
                       help='Probar endpoints HTTP del servidor')
    parser.add_argument('--stdio', action='store_true',
                       help='Iniciar servidor MCP en modo stdio')
    parser.add_argument('--help-setup', action='store_true',
                       help='Mostrar ayuda para configuración inicial')
    parser.add_argument('--install-deps', action='store_true',
                       help='Instalar dependencias requeridas')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check if we're in the right directory
    if not Path("tools_mcp.py").exists():
        print("❌ Error: Ejecuta este script desde el directorio mcp/")
        print("💡 Usa: cd mcp && python mcp_cli.py")
        return False
    
    # Handle help-setup
    if args.help_setup:
        print("""
🔧 CONFIGURACIÓN INICIAL
=======================

1. Variables de Entorno Requeridas:
   export GOOGLE_API_KEY="tu-google-api-key"
   export MCP_TOKEN="tu-token-seguro" 
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   export SMTP_USERNAME="tu-email@gmail.com"
   export SMTP_PASSWORD="tu-password-app"

2. Activar Entorno Virtual:
   cd /home/daniel/projects/Coches_segunda_mano_ia
   source myenv/bin/activate
   cd mcp

3. Instalar Dependencias:
   python mcp_cli.py --install-deps

4. Probar Sistema:
   python mcp_cli.py --test

5. Iniciar Servidor:
   python mcp_cli.py --server

📚 Documentación completa en README.md
        """)
        return True
    
    # Handle install-deps
    if args.install_deps:
        commands = [
            "pip install httpx beautifulsoup4 fastapi uvicorn gradio aiofiles google-generativeai openai",
            "pip install -r requirements.txt"
        ]
        
        for cmd in commands:
            success = run_command(cmd, "Instalación de dependencias")
            if not success:
                print("❌ Error instalando dependencias")
                return False
        
        print("✅ Todas las dependencias instaladas correctamente")
        return True
    
    # Handle test
    if args.test:
        return run_command("python test_mcp_system.py", "Pruebas completas del sistema")
    
    # Handle server
    if args.server:
        print("🌐 Iniciando servidor MCP HTTP...")
        print("📚 Documentación: http://localhost:8000/docs")
        print("❤️ Health check: http://localhost:8000/health")
        print("⚡ Presiona Ctrl+C para detener")
        return run_command("python start_server.py", "Servidor HTTP")
    
    # Handle stdio
    if args.stdio:
        print("📡 Iniciando servidor MCP en modo stdio...")
        print("⚡ Para uso con Claude Desktop u otros clientes MCP")
        return run_command("python mcp_server.py", "Servidor stdio")
    
    # Handle UI
    if args.ui:
        print("🎨 Iniciando interfaz web Gradio...")
        return run_command("python ui/launch.py", "Interfaz web")
    
    # Handle demo
    if args.demo:
        return run_command("python demo.py", "Script de demostración")
    
    # Handle test-endpoints
    if args.test_endpoints:
        print("⚠️ Nota: Asegúrate de que el servidor esté ejecutándose")
        print("💡 Ejecuta en otra terminal: python mcp_cli.py --server")
        input("📝 Presiona Enter cuando el servidor esté listo...")
        return run_command("python test_mcp_server_endpoints.py", "Pruebas de endpoints HTTP")
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n💡 Comandos más comunes:")
        print("   python mcp_cli.py --test     # Probar sistema")
        print("   python mcp_cli.py --server   # Iniciar servidor")
        print("   python mcp_cli.py --ui       # Abrir interfaz web")
        return True
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Programa cancelado por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)