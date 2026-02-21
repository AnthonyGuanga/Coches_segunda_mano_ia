#!/usr/bin/env python3
"""
Setup script para el proyecto MCP Vehicle Safety Analysis
Automatiza la configuración inicial del entorno
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e.stderr}")
        return False

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ requerido")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    return True

def setup_virtual_environment():
    """Setup virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("⚠️ Virtual environment ya existe")
        return True
    
    if not run_command(f"{sys.executable} -m venv venv", "Creando virtual environment"):
        return False
    
    return True

def install_dependencies():
    """Install project dependencies"""
    activate_cmd = "venv/bin/activate" if os.name != 'nt' else "venv\\Scripts\\activate"
    pip_cmd = "venv/bin/pip" if os.name != 'nt' else "venv\\Scripts\\pip"
    
    if not run_command(f"{pip_cmd} install --upgrade pip", "Actualizando pip"):
        return False
    
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Instalando dependencias"):
        return False
    
    return True

def setup_environment_file():
    """Setup .env file"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("⚠️ Archivo .env ya existe")
        return True
    
    if env_example.exists():
        if run_command(f"cp .env.example .env", "Copiando archivo de configuración"):
            print("📝 Edita .env con tus configuraciones específicas")
            return True
    
    return False

def create_output_directory():
    """Create output directory"""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    print("✅ Directorio de outputs creado")
    return True

def run_tests():
    """Run basic tests"""
    python_cmd = "venv/bin/python" if os.name != 'nt' else "venv\\Scripts\\python"
    
    print("🧪 Ejecutando tests básicos...")
    if run_command(f"{python_cmd} -m pytest tests/ -v --tb=short", "Tests"):
        print("✅ Todos los tests pasaron")
        return True
    else:
        print("⚠️ Algunos tests fallaron (esto puede ser normal si no hay APIs configuradas)")
        return True  # No es crítico para el setup

def display_next_steps():
    """Display next steps for user"""
    python_cmd = "venv/bin/python" if os.name != 'nt' else "venv\\Scripts\\python"
    activate_cmd = "source venv/bin/activate" if os.name != 'nt' else "venv\\Scripts\\activate"
    
    print("\n" + "="*60)
    print("🎉 Setup completado exitosamente!")
    print("="*60)
    
    print("\n📋 Próximos pasos:")
    print(f"1. Activar entorno virtual:")
    print(f"   {activate_cmd}")
    
    print(f"\n2. Configurar variables de entorno (opcional):")
    print(f"   nano .env")
    
    print(f"\n3. Ejecutar servidor MCP:")
    print(f"   {python_cmd} mcp_server.py --http")
    
    print(f"\n4. En otra terminal, lanzar interfaz Gradio:")
    print(f"   {python_cmd} ui/launch.py")
    
    print(f"\n5. O ejecutar demo interactivo:")
    print(f"   {python_cmd} demo.py")
    
    print(f"\n📚 Más información:")
    print(f"   - README.md - Documentación completa")
    print(f"   - .env.example - Variables de configuración")
    print(f"   - tests/ - Tests para validar funcionamiento")
    
    print(f"\n🌐 URLs importantes:")
    print(f"   - MCP Server: http://localhost:8000")
    print(f"   - Gradio UI: http://localhost:7860")
    print(f"   - Health Check: http://localhost:8000/health")

def main():
    """Main setup function"""
    print("🚗 MCP Vehicle Safety Analysis System - Setup")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"📁 Working directory: {script_dir}")
    
    # Run setup steps
    steps = [
        ("Verificando versión de Python", check_python_version),
        ("Configurando virtual environment", setup_virtual_environment),
        ("Instalando dependencias", install_dependencies),
        ("Configurando archivo .env", setup_environment_file),
        ("Creando directorio de outputs", create_output_directory),
    ]
    
    failed_steps = []
    
    for description, func in steps:
        print(f"\n🔧 {description}...")
        if not func():
            failed_steps.append(description)
    
    # Optional: run tests
    print(f"\n🧪 ¿Ejecutar tests? (y/N): ", end="")
    try:
        if input().lower().startswith('y'):
            run_tests()
    except KeyboardInterrupt:
        print("\n⚠️ Tests omitidos")
    
    # Summary
    if failed_steps:
        print(f"\n⚠️ Algunos pasos fallaron:")
        for step in failed_steps:
            print(f"   - {step}")
        print(f"\nRevisa los errores e intenta configurar manualmente.")
    else:
        display_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n👋 Setup cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)