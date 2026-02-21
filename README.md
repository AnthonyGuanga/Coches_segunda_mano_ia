# 🚗 MCP Vehicle Safety Analysis System

**Sistema completo de análisis de seguridad vehicular implementado con Model Context Protocol (MCP)**

## 📋 Descripción

Este proyecto implementa un ecosistema MCP completo para el análisis de seguridad vehicular que incluye:

- **Servidor MCP** con soporte para transporte stdio y HTTP streamable
- **Múltiples herramientas MCP** de diferentes categorías (API externa, procesamiento LLM, acciones reales)
- **Integración LangGraph** para workflows complejos de agentes
- **Interfaz Gradio** para interacción web
- **Tests comprehensivos** con mocking de servicios externos
- **Documentación completa** y ejemplos de uso

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Gradio UI     │    │  LangGraph       │    │  MCP Client     │
│   (Web Client)  │◄──►│  Agent           │◄──►│  Applications   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ stdio       │  │ HTTP        │  │ Server-Sent Events      │ │
│  │ Transport   │  │ Transport   │  │ (Streaming)            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Vehicle Safety  │  │ LLM Extraction  │  │ Report & Email  │
│ API (NHTSA)     │  │ (Gemini/OpenAI) │  │ Generation      │
│ External APIs   │  │ Processing      │  │ Real Actions    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 🛠️ Herramientas MCP Implementadas

### 1. API Externa - `check_vehicle_safety`
- **Categoría**: External API
- **Función**: Consulta recalls y calificaciones de seguridad de NHTSA
- **Input**: make, model, year, vin (opcional)
- **Output**: Recalls, safety ratings, recomendaciones

### 2. Procesamiento LLM - `llm_extract_vehicle_info`
- **Categoría**: LLM Processing  
- **Función**: Extrae información vehicular de texto libre usando LLM
- **Providers**: Gemini AI, OpenAI (fallback), Regex (fallback)
- **Input**: Texto en lenguaje natural
- **Output**: Marca, modelo, año, VIN extraídos

### 3. Acción Real - `send_email_smtp`
- **Categoría**: Real Action
- **Función**: Envía notificaciones por email con reportes
- **Features**: Soporte para adjuntos, modo simulación
- **Input**: Destinatario, asunto, cuerpo, adjunto
- **Output**: Confirmación de envío

### 4. Generación - `generate_markdown_report`
- **Categoría**: Content Generation
- **Función**: Genera reportes en formato Markdown
- **Input**: Título, contenido, metadata
- **Output**: Archivo .md generado

### 5. Web Fetching - `web_fetch`
- **Categoría**: External Resource
- **Función**: Obtiene contenido web para análisis
- **Input**: URL
- **Output**: Contenido HTML procesado

## 🚀 Instalación y Configuración

### 1. Configurar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv myenv

# Activar entorno
source myenv/bin/activate  # Linux/Mac
# o
myenv\Scripts\activate     # Windows
```

### 2. Instalar Dependencias

```bash
# Instalar dependencias principales
pip install -r requirements.txt

# O usando uv (más rápido)
uv sync
```

### 3. Variables de Entorno Necesarias

Crear archivo `.env` en el directorio raíz:

```bash
# MCP Configuration
MCP_TOKEN=your-secure-token-here
MCP_PORT=8000

# NHTSA API Configuration  
NHTSA_BASE_URL=https://api.nhtsa.gov/SafetyRatings

# LLM Configuration (opcional - para llm_extract_vehicle_info)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# SMTP Configuration
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_FROM=vehicle-safety@mcp.local

# Output Configuration
OUTPUT_DIR=./outputs
```

## 🎯 Cómo Ejecutar

### Servidor MCP en modo stdio (local)

```bash
# Ejecutar servidor stdio para clientes MCP locales
python mcp_server.py --stdio

# O con logging detallado
python mcp_server.py --stdio --verbose
```

### Servidor MCP en modo HTTP streamable

```bash
# Ejecutar servidor HTTP con Server-Sent Events
python mcp_server.py --http

# Servidor estará disponible en http://localhost:8000
# Endpoints:
# - GET /health - Health check
# - GET /tools - Listar herramientas (requiere auth)
# - POST /call-tool - Ejecutar herramienta (requiere auth)  
# - GET /events - Server-Sent Events stream
```

### Interfaz Gradio

```bash
# Lanzar interfaz web completa
python ui/launch.py

# O directamente
python ui/gradio_app.py

# Interfaz disponible en http://localhost:7860
```

### Agente LangGraph

```bash
# Ejecutar análisis con agente completo
python -c "
from agents.langgraph_adapter import VehicleSafetyAgent
import asyncio

async def main():
    agent = VehicleSafetyAgent('http://localhost:8000', 'your-token')
    result = await agent.run_analysis('BMW Serie 3 2020 seguridad')
    print(result)

asyncio.run(main())
"
```

## 📝 Ejemplos de Uso

### 1. Curl - Listar herramientas

```bash
curl -X GET "http://localhost:8000/tools" \
  -H "Authorization: Bearer your-secure-token-here" \
  -H "Content-Type: application/json"
```

### 2. Curl - Consultar seguridad vehicular

```bash
curl -X POST "http://localhost:8000/call-tool" \
  -H "Authorization: Bearer your-secure-token-here" \
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

### 3. Curl - Extraer info con LLM

```bash
curl -X POST "http://localhost:8000/call-tool" \
  -H "Authorization: Bearer your-secure-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "llm_extract_vehicle_info",
    "arguments": {
      "text": "Quiero revisar la seguridad de un Toyota Corolla 2019"
    }
  }'
```

### 4. Curl - Generar reporte

```bash
curl -X POST "http://localhost:8000/call-tool" \
  -H "Authorization: Bearer your-secure-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "generate_markdown_report",
    "arguments": {
      "title": "Reporte BMW Serie 3 2020",
      "content": "# Análisis de Seguridad\n\nNo se encontraron recalls..."
    }
  }'
```

### 5. Cliente MCP en Python

```python
import asyncio
from agents.langgraph_adapter import MCPClient

async def main():
    client = MCPClient("http://localhost:8000", "your-token")
    
    # Listar herramientas
    tools = await client.list_tools()
    print("Herramientas disponibles:", [t["name"] for t in tools])
    
    # Ejecutar análisis completo
    result = await client.call_tool(
        "check_vehicle_safety",
        {"make": "Tesla", "model": "Model 3", "year": 2022}
    )
    
    print("Resultado:", result)
    await client.close()

asyncio.run(main())
```

## 🧪 Testing

### Ejecutar Tests Completos

```bash
# Instalar dependencias de test
pip install pytest pytest-asyncio pytest-cov

# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=. --cov-report=html

# Solo tests unitarios
pytest tests/test_tools.py -v

# Solo tests del servidor MCP
pytest tests/test_mcp_server.py -v
```

### Tests Específicos

```bash
# Test herramienta de seguridad con mock
pytest tests/test_tools.py::TestCheckVehicleSafety::test_successful_vehicle_lookup -v

# Test servidor SMTP simulado 
pytest tests/test_tools.py::TestSendEmailSMTP::test_simulation_mode -v

# Test extractor LLM con fallbacks
pytest tests/test_tools.py::TestLLMExtractVehicleInfo::test_regex_fallback -v

# Test endpoints FastAPI
pytest tests/test_mcp_server.py::TestMCPFastAPIIntegration -v
```

### Configurar Mock SMTP Server para Tests

```bash
# Instalar y ejecutar servidor SMTP de desarrollo
pip install aiosmtpd

# Ejecutar servidor mock en otra terminal
python -m aiosmtpd -n -l localhost:1025

# Los emails se mostrarán en consola
```

## 🔧 Configuración de Cliente MCP

### VS Code con MCP Extension

1. Instalar extensión MCP para VS Code
2. Configurar en `settings.json`:

```json
{
  "mcp.servers": {
    "vehicle-safety": {
      "command": "python",
      "args": ["mcp_server.py", "--stdio"],
      "cwd": "/path/to/project"
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
      "args": ["/path/to/project/mcp_server.py", "--stdio"],
      "env": {
        "MCP_TOKEN": "your-token"
      }
    }
  }
}
```

### Continue.dev

Configurar en `config.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "vehicle-safety",
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["mcp_server.py", "--stdio"]
        }
      }
    ]
  }
}
```

## 📊 Estructura del Proyecto

```
Coches_segunda_mano_ia/
├── mcp_server.py              # Servidor MCP principal
├── tools.py                   # Implementación de herramientas
├── pyproject.toml            # Configuración del proyecto
├── requirements.txt          # Dependencias
├── .env                      # Variables de entorno
├── README.md                 # Este archivo
│
├── agents/                   # Integración LangGraph
│   ├── __init__.py
│   └── langgraph_adapter.py
│
├── ui/                       # Interfaz Gradio
│   ├── __init__.py
│   ├── gradio_app.py
│   └── launch.py
│
├── tests/                    # Tests comprehensivos
│   ├── __init__.py
│   ├── test_tools.py         # Tests de herramientas
│   └── test_mcp_server.py    # Tests del servidor
│
├── outputs/                  # Reportes generados
│   └── *.md
│
└── data/                     # Datos del proyecto
    ├── *.csv
    └── faiss_index/
```

## 🔐 Seguridad y Autenticación

### Tokens de Acceso

- **Desarrollo**: `default-token`
- **Producción**: Usar variable `MCP_TOKEN` con token seguro
- **Headers**: `Authorization: Bearer <token>`

### CORS Configuration

```python
# Configurado para desarrollo local
origins = [
    "http://localhost",
    "http://localhost:3000", 
    "http://localhost:7860",
    "http://127.0.0.1"
]
```

### Rate Limiting (Futuro)

```python
# Implementación sugerida para producción
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/call-tool")
@limiter.limit("10/minute")
async def call_tool_endpoint():
    pass
```

## 🚀 Deploy y Producción

### Docker (Futuro)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "mcp_server.py", "--http"]
```

### Variables de Entorno Producción

```bash
# Seguridad
MCP_TOKEN=secure-production-token-here
CORS_ORIGINS=https://yourdomain.com

# APIs Externas  
NHTSA_BASE_URL=https://api.nhtsa.gov/SafetyRatings
GEMINI_API_KEY=production-gemini-key
OPENAI_API_KEY=production-openai-key

# Email Real
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/mcp-server.log
```

## 🔄 Workflow Completo

### Análisis de Seguridad Integral

1. **Input del Usuario**: Texto libre o campos específicos
2. **Extracción LLM**: Identificar marca, modelo, año, VIN
3. **Consulta NHTSA**: Obtener recalls y safety ratings
4. **Generación de Reporte**: Crear documento Markdown
5. **Notificación**: Enviar email con reporte adjunto
6. **Output**: Resultados en UI + archivo descargable

### Ejemplo Completo

```python
# Workflow automático con agente
from agents.langgraph_adapter import VehicleSafetyAgent

agent = VehicleSafetyAgent("http://localhost:8000", "your-token")

# Análisis completo desde texto libre
result = await agent.run_analysis(
    "Necesito verificar la seguridad de mi BMW X5 2021, VIN: 5UXCR6C04M9D12345"
)

# Resultado incluye:
# - Información extraída del vehículo
# - Datos de seguridad de NHTSA  
# - Reporte en Markdown
# - Confirmación de email enviado
print(result)
```

## 🤝 Contribuciones

### Agregar Nueva Herramienta MCP

1. Implementar función en `tools.py`:
```python
async def nueva_herramienta(param1: str, param2: int) -> dict:
    # Implementación
    return {"success": True, "data": result}
```

2. Agregar a `tools_dict` en `tools.py`
3. Crear tests en `tests/test_tools.py`
4. Actualizar documentación

### Agregar Nuevo Transport

1. Extender `MCPServer` en `mcp_server.py`
2. Implementar protocolo específico
3. Agregar tests de integración
4. Documentar configuración

## 📚 Referencias

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Gradio Documentation](https://gradio.app/)
- [NHTSA API Documentation](https://vpic.nhtsa.dot.gov/api/)

## 📄 Licencia

MIT License - Ver archivo `LICENSE` para detalles.

## 🐛 Troubleshooting

### Error: "MCP server not accessible"
- Verificar que el servidor esté ejecutándose
- Comprobar puerto y URL correctos
- Validar token de autorización

### Error: "Tool execution failed"  
- Revisar logs del servidor: `python mcp_server.py --http --verbose`
- Verificar variables de entorno necesarias
- Comprobar conectividad a APIs externas

### Error: "LLM extraction failed"
- Verificar API keys de Gemini/OpenAI
- El sistema usa regex como fallback automático
- Revisar formato del texto de entrada

### Error: "Email sending failed"
- Para desarrollo: usar modo simulación (SMTP_HOST=localhost)
- Para producción: configurar credenciales SMTP reales
- Verificar firewall y conectividad SMTP

---

**¡Sistema MCP de Análisis de Seguridad Vehicular - Listo para usar! 🚗✨**

- `Year`: Año del coche  
- `Present_Price`: Precio original del coche  
- `Kms_Driven`: Kilómetros recorridos  
- `Fuel_Type`: Tipo de combustible  
- `Seller_Type`: Tipo de vendedor  
- `Transmission`: Tipo de transmisión  
- `Owner`: Número de propietarios anteriores  
- `Selling_Price`: Precio de venta (variable objetivo)  

**Motivación:** Elegimos este dataset porque contiene información suficiente para construir un modelo de regresión robusto y permite explorar cómo diferentes características de un coche afectan a su precio. Además, su tamaño es adecuado para entrenar modelos de machine learning sin requerir recursos computacionales elevados.

---

## Definición del Problema
Queremos responder a la pregunta:  
**“¿Cuál será el precio de venta de un coche de segunda mano dado sus características?”**

- Tipo de problema: **Regresión**, ya que la variable objetivo (`Selling_Price`) es continua.  
- Variables explicativas: todas las columnas excepto `Selling_Price`.  
- Variable dependiente: `Selling_Price`.

---

## Exploración de Datos (EDA)
Durante la exploración inicial:

- Se analizaron estadísticas descriptivas de todas las variables.  
- Se visualizó la distribución de los precios y los kilómetros recorridos.  
- Se identificaron outliers en `Kms_Driven` y `Present_Price`.  
- Se examinó la relación entre variables categóricas (`Fuel_Type`, `Seller_Type`, `Transmission`) y el precio de venta mediante gráficos de caja y correlaciones.

---

## Preprocesamiento
Antes de entrenar los modelos:

- Se eliminaron valores nulos y registros duplicados.  
- Las variables categóricas (`Fuel_Type`, `Seller_Type`, `Transmission`) fueron codificadas usando **One-Hot Encoding**.  
- Se normalizaron las variables numéricas para mejorar la convergencia del modelo.  
- Se dividió el dataset en **80% entrenamiento y 20% prueba**.

---

## Entrenamiento de Modelos
Entrenamos y evaluamos varios modelos de regresión:

1. **Regresión Lineal**
   - Hiperparámetros: predeterminados (`fit_intercept=True`)  
   - Permite una interpretación directa de la influencia de cada variable sobre el precio.

2. **Random Forest Regressor**
   - Hiperparámetros: `n_estimators=100`, `max_depth=10`, `random_state=42`  
   - Captura relaciones no lineales entre variables y precio.  

---

## Evaluación del Modelo
Métricas utilizadas:

- **MAE (Mean Absolute Error)**  
- **RMSE (Root Mean Squared Error)**  
- **R² (Coeficiente de determinación)**

**Resultados destacados:**

- El **Random Forest** presentó mejor desempeño que la regresión lineal, mostrando menor error medio y mayor R².  
- Las variables que más influyen en el precio son `Present_Price`, `Kms_Driven` y `Year`.  
- El modelo captura la tendencia general, aunque los coches con precios extremadamente altos o bajos presentan errores mayores.

---

## Conclusiones
- El proyecto permite predecir precios de coches de segunda mano de manera razonablemente precisa.  
- Las características más relevantes para la predicción son el precio original, los kilómetros recorridos y el año del vehículo.  
- Posibles mejoras: ampliar el dataset con más coches, probar modelos avanzados como XGBoost, y realizar ingeniería de características adicional (por ejemplo, antigüedad del coche, mercado de segunda mano por región).  

---

