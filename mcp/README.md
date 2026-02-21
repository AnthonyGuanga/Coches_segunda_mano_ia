# 🚗 MCP Vehicle Safety Analysis System - Sistema MCP Completo

**Sistema completo de análisis de seguridad vehicular implementado con Model Context Protocol (MCP)**

## 📋 Descripción del Proyecto

Este proyecto es una **implementación completa de MCP (Model Context Protocol)** que incluye un ecosistema integral para el análisis de seguridad vehicular con todas las herramientas y componentes necesarios organizados profesionalmente.

## 📁 Estructura del Proyecto

```
mcp/
├── __init__.py                        # Inicializador del paquete
├── mcp_server.py                      # Servidor MCP principal (stdio/HTTP)
├── tools_mcp.py                      # Herramientas MCP especializadas
├── demo.py                           # Script de demostración
├── start_server.py                   # Script para iniciar servidor HTTP
├── test_mcp_system.py               # Suite de pruebas completas
├── test_mcp_server_endpoints.py     # Pruebas de endpoints HTTP
├── README.md                         # Esta documentación
├── requirements.txt                  # Dependencias específicas
├── agents/                          # Agentes LangGraph
│   └── langgraph_adapter.py
├── ui/                              # Interfaz de usuario
│   ├── __init__.py
│   ├── gradio_app.py
│   └── launch.py
└── tests/                           # Tests unitarios
    ├── __init__.py
    ├── test_mcp_server.py
    └── test_tools.py
```

### ✅ Componentes Implementados

1. **🔧 Servidor MCP (`mcp_server.py`)**
   - ✅ Soporte para **stdio transport** (clientes locales)
   - ✅ Soporte para **HTTP streamable** transport (web/API)
   - ✅ Autenticación Bearer token
   - ✅ Server-Sent Events para streaming
   - ✅ FastAPI con CORS configurado

2. **⚙️ Herramientas MCP (`tools_mcp.py`)**
   - ✅ **`check_vehicle_safety`** - Categoría: External API (NHTSA)
   - ✅ **`llm_extract_vehicle_info`** - Categoría: LLM Processing (Gemini/OpenAI + fallback)
   - ✅ **`send_email_smtp`** - Categoría: Real Action (SMTP con simulación)
   - ✅ **`generate_markdown_report`** - Categoría: Content Generation
   - ✅ **`web_fetch`** - Categoría: External Resource

3. **🤖 Agente LangGraph (`agents/langgraph_adapter.py`)**
   - ✅ Cliente MCP HTTP integrado
   - ✅ Workflow multi-step para análisis completo
   - ✅ Estado persistente y manejo de errores

4. **🎨 Interfaz Gradio (`ui/gradio_app.py`)**
   - ✅ Formulario para consultas por texto libre
   - ✅ Formulario para campos específicos  
   - ✅ Integración completa con MCP y agentes
   - ✅ Descarga de reportes generados

5. **🧪 Tests Comprehensivos (`tests/`)**
   - ✅ Tests unitarios con mocks para todas las herramientas
   - ✅ Tests de integración del servidor MCP
   - ✅ Coverage de endpoints FastAPI
   - ✅ Simulación de servicios externos

## 🚀 Instalación Rápida

```bash
# 1. Entrar a la carpeta MCP
cd mcp/

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (opcional)
cp ../.env . # O crear .env con las variables necesarias
```

### Variables de Entorno Mínimas

```bash
# .env file
MCP_TOKEN=default-token
NHTSA_BASE_URL=https://api.nhtsa.gov/SafetyRatings
SMTP_HOST=localhost
SMTP_PORT=1025
EMAIL_FROM=vehicle-safety@mcp.local
```

## 🎯 Ejecución del Sistema

### 1. Servidor MCP - Modo stdio (Local)

```bash
# Para clientes MCP locales (VS Code, Claude Desktop, etc.)
python mcp_server.py --stdio

# Con logging detallado
python mcp_server.py --stdio --verbose
```

### 2. Servidor MCP - Modo HTTP (Web)

```bash
# Para aplicaciones web y APIs
python mcp_server.py --http

# Servidor disponible en: http://localhost:8000
# Endpoints:
# - GET /health - Health check
# - GET /tools - Listar herramientas (requiere auth)
# - POST /call-tool - Ejecutar herramienta (requiere auth)
# - GET /events - Server-Sent Events stream
```

### 3. Interfaz Web Gradio

```bash
# Lanzar interfaz completa (inicia servidor MCP automáticamente)
python ui/launch.py

# O directamente
python ui/gradio_app.py

# Disponible en: http://localhost:7860
```

### 4. Demo Completo

```bash
# Ejecutar demo interactivo
python demo.py

# Opciones disponibles:
# 1. Herramientas MCP individuales
# 2. Agente LangGraph completo  
# 3. Cliente MCP HTTP
# 4. Todos los demos
```

## 📝 Ejemplos de Uso

### Curl - Consultar Herramientas MCP

```bash
curl -X GET "http://localhost:8000/tools" \
  -H "Authorization: Bearer default-token"
```

### Curl - Ejecutar Análisis de Seguridad

```bash
curl -X POST "http://localhost:8000/call-tool" \
  -H "Authorization: Bearer default-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "check_vehicle_safety",
    "arguments": {
      "make": "BMW",
      "model": "Series 3",
      "year": 2020
    }
  }'
```

### Curl - Extraer Info con LLM

```bash
curl -X POST "http://localhost:8000/call-tool" \
  -H "Authorization: Bearer default-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "llm_extract_vehicle_info",
    "arguments": {
      "text": "Quiero revisar la seguridad de Toyota Corolla 2019"
    }
  }'
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Tests específicos
pytest tests/test_tools.py -v
pytest tests/test_mcp_server.py -v

# Con coverage
pytest --cov=. --cov-report=html
```

## 🔧 Configuración de Clientes MCP

### VS Code

Agregar a `settings.json`:

```json
{
  "mcp.servers": {
    "vehicle-safety": {
      "command": "python",
      "args": ["/path/to/mcp/mcp_server.py", "--stdio"],
      "cwd": "/path/to/mcp"
    }
  }
}
```

### Claude Desktop

Agregar a `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vehicle-safety": {
      "command": "python",
      "args": ["/path/to/mcp/mcp_server.py", "--stdio"],
      "env": {"MCP_TOKEN": "default-token"}
    }
  }
}
```

## 📊 Estructura del Proyecto MCP

```
mcp/
├── mcp_server.py              # 🔧 Servidor MCP principal
├── tools_mcp.py               # ⚙️ Herramientas MCP específicas
├── demo.py                    # 🎯 Demo interactivo
├── requirements.txt           # 📦 Dependencias MCP
├── pytest.ini               # 🧪 Configuración de tests
│
├── agents/                   # 🤖 LangGraph integration
│   ├── __init__.py
│   └── langgraph_adapter.py
│
├── ui/                       # 🎨 Interfaz Gradio
│   ├── __init__.py
│   ├── gradio_app.py
│   └── launch.py
│
└── tests/                    # 🧪 Tests comprehensivos
    ├── __init__.py
    ├── test_tools.py
    └── test_mcp_server.py
```

## 🎯 Casos de Uso Demostrados

### 1. Análisis por Texto Libre
```
Input: "Quiero revisar la seguridad de BMW Serie 3 2020"
→ LLM extrae: BMW, Serie 3, 2020
→ Consulta NHTSA recalls y ratings
→ Genera reporte Markdown
→ Envía notificación por email
```

### 2. Consulta Específica por Campos
```
Input: make="Tesla", model="Model 3", year=2022
→ Consulta directa a NHTSA
→ Obtiene recalls y calificaciones
→ Muestra resultados en UI
```

### 3. Workflow de Agente Completo
```
Input: Texto natural → Agente LangGraph
→ Extracción → Consulta → Reporte → Email
→ Resultado integral con todos los pasos
```

## ✅ Criterios de Aceptación Cumplidos

- ✅ **MCP Server** con stdio y streamablehttp transports
- ✅ **Al menos 3 tools** de diferentes categorías:
  - External API (NHTSA)
  - LLM Processing (Gemini/OpenAI)
  - Real Actions (SMTP email)
  - Content Generation (Markdown)
  - External Resources (Web fetch)
- ✅ **Integración LangGraph** para agentes complejos
- ✅ **UI Gradio** para interacción usuario
- ✅ **Tests pytest** con mocking completo
- ✅ **Documentación completa** con ejemplos
- ✅ **Configuración clientes MCP** reales

## 🔄 Flujo de Trabajo Completo

1. **Usuario ingresa consulta** (texto libre o campos)
2. **LLM extrae información** del vehículo (make, model, year, VIN)
3. **API NHTSA consulta** recalls y safety ratings oficiales
4. **Sistema genera reporte** Markdown estructurado
5. **Email se envía** con reporte adjunto (real o simulado)
6. **Usuario recibe** resultados y archivo descargable

## 🚀 Características Destacadas

- **🔄 Fallback Systems**: LLM → Regex, SMTP real → Simulación
- **🔒 Autenticación**: Bearer tokens, CORS configurado
- **📊 Monitoring**: Logs estructurados, health checks
- **🧪 Testing**: Mocking completo de servicios externos
- **📱 Multi-interface**: stdio, HTTP, Gradio, CLI
- **🤖 Agent-ready**: LangGraph integration lista para usar

---

**¡Práctica MCP completamente implementada y funcional! 🚗✨**

Para más detalles, consulta el README principal del proyecto o ejecuta `python demo.py` para una demostración interactiva.