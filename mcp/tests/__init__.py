"""
Test suite para el sistema MCP de análisis vehicular
"""

# Test configuration
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test environment setup
os.environ.setdefault('MCP_TOKEN', 'test-token')
os.environ.setdefault('NHTSA_BASE_URL', 'https://api.nhtsa.gov/SafetyRatings')
os.environ.setdefault('SMTP_HOST', 'localhost')
os.environ.setdefault('SMTP_PORT', '1025')
os.environ.setdefault('EMAIL_FROM', 'test@mcp.local')