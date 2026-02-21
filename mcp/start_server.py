#!/usr/bin/env python3
"""
Script para iniciar el servidor MCP HTTP con configuración optimizada
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import uvicorn
    from mcp_server import app
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Please install dependencies:")
    print("   pip install uvicorn fastapi")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment configuration...")
    
    # Check required environment variables
    required_vars = [
        "GOOGLE_API_KEY",
        "MCP_TOKEN", 
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️ Missing environment variables (using fallbacks):")
        for var in missing_vars:
            print(f"   - {var}")
    else:
        print("✅ All environment variables configured")
    
    return True

def main():
    """Main function to start the MCP server"""
    print("🚀 MCP Server Starter")
    print("=" * 40)
    
    # Check environment
    check_environment()
    
    # Configuration
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    print(f"🌐 Starting MCP server on http://{host}:{port}")
    print(f"📚 API documentation: http://{host}:{port}/docs")
    print(f"❤️ Health check: http://{host}:{port}/health")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 40)
    
    try:
        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            reload=False,  # Set to True for development
            server_header=False,
            date_header=False
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()