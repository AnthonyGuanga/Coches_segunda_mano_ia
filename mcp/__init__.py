"""
MCP Vehicle Safety Analysis System
Práctica completa de Model Context Protocol (MCP)

Este módulo contiene un ecosistema MCP completo para análisis de seguridad vehicular:
- Servidor MCP con soporte stdio y HTTP
- Herramientas MCP de diferentes categorías
- Integración LangGraph para agentes
- Interfaz Gradio para usuarios finales
- Tests comprehensivos
"""

from .tools_mcp import (
    check_vehicle_safety,
    llm_extract_vehicle_info,
    send_email_smtp,
    generate_markdown_report,
    web_fetch,
    mcp_tools_dict,
    mcp_tools_descriptions,
    format_mcp_tool_output
)

__version__ = "1.0.0"
__author__ = "MCP Practice Project"

__all__ = [
    "check_vehicle_safety",
    "llm_extract_vehicle_info", 
    "send_email_smtp",
    "generate_markdown_report",
    "web_fetch",
    "mcp_tools_dict",
    "mcp_tools_descriptions", 
    "format_mcp_tool_output"
]