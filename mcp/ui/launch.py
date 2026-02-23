#!/usr/bin/env python3
"""
Script de lanzamiento para la interfaz Gradio
Maneja la inicialización del servidor MCP si es necesario
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the correct path
# Get the project root (three levels up from mcp/ui/launch.py)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

def check_mcp_server(url: str = "http://localhost:8000") -> bool:
    """Check if MCP server is running"""
    try:
        import httpx
        with httpx.Client() as client:
            response = client.get(f"{url}/health", timeout=5)
            return response.status_code == 200
    except Exception:
        return False

def start_mcp_server():
    """Start MCP server in background"""
    print("🚀 Starting MCP server...")
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        "MCP_TOKEN": "default-token",
        "NHTSA_BASE_URL": "https://api.nhtsa.gov/SafetyRatings",
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "1025",
        "EMAIL_FROM": "vehicle-safety@mcp.local"
    })
    
    # Start server
    process = subprocess.Popen(
        [sys.executable, "mcp/mcp_server.py", "--http"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    for i in range(30):  # 30 second timeout
        if check_mcp_server():
            print("✅ MCP server is running")
            return process
        time.sleep(1)
        print(f"⏳ Waiting for MCP server... ({i+1}/30)")
    
    print("❌ Failed to start MCP server")
    process.terminate()
    return None

def main():
    """Main launcher"""
    print("🚗 Vehicle Safety Analysis - MCP UI Launcher")
    print("=" * 50)
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    print(f"📁 Working directory: {project_root}")
    
    # Check if we're in the right directory now
    mcp_server_path = Path("mcp/mcp_server.py")
    if not mcp_server_path.exists():
        print("❌ Error: mcp/mcp_server.py not found")
        print("Please check your project structure")
        sys.exit(1)
    
    # Check/start MCP server
    mcp_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    
    if not check_mcp_server(mcp_url):
        print(f"📡 MCP server not found at {mcp_url}")
        
        if mcp_url == "http://localhost:8000":
            # Try to start local server
            server_process = start_mcp_server()
            if not server_process:
                print("❌ Cannot start MCP server. Please start it manually:")
                print("   python mcp_server.py --http")
                sys.exit(1)
        else:
            print(f"❌ MCP server at {mcp_url} is not accessible")
            sys.exit(1)
    else:
        print(f"✅ MCP server is running at {mcp_url}")
    
    # Launch Gradio UI
    print("\n🎨 Starting Gradio interface...")
    try:
        # Add mcp/ui to Python path
        ui_path = Path("mcp/ui")
        sys.path.insert(0, str(ui_path))
        from gradio_app import main as ui_main
        ui_main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required dependencies:")
        print("   pip install gradio")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error starting UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()