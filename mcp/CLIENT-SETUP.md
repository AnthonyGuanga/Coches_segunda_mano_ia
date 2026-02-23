# 🔌 **Guía de Conexión con Clientes MCP**

## **📋 Clientes soportados**

### **1. Claude Desktop**
```bash
# 1. Copiar configuración
cp claude-config.json ~/.config/Claude/claude_desktop_config.json

# 2. Asegurar que tienes GOOGLE_API_KEY en tu .env
export GOOGLE_API_KEY="your-api-key-here"

# 3. Reiniciar Claude Desktop
# 4. El servidor aparecerá como "vehicle-safety" en la lista de MCPs
```

### **2. VS Code MCP Extension**
```bash
# 1. Instalar extensión MCP en VS Code
# 2. Abrir Command Palette (Ctrl+Shift+P)
# 3. Ejecutar "MCP: Add Server"
# 4. Usar la configuración en vscode-mcp-config.json
```

### **3. Cherry Studio**
```bash
# Configuración HTTP:
# - URL: http://localhost:8000
# - Token: default-token
# - Transport: HTTP
```

### **4. MCP Inspector**
```bash
# Para probar el servidor (desde el directorio mcp):
npx @modelcontextprotocol/inspector python mcp_server.py --stdio
```

## **🧪 Pruebas rápidas**

### **Ejecutar script de pruebas:**
```bash
./test-mcp-clients.sh
```

### **Probar manualmente:**
```bash
# 1. Iniciar servidor HTTP (desde el directorio mcp)
python mcp_server.py --http

# 2. En otra terminal - probar endpoints:
curl -H "Authorization: Bearer default-token" http://localhost:8000/tools
curl -H "Authorization: Bearer default-token" http://localhost:8000/health
curl -H "Authorization: Bearer default-token" http://localhost:8000/stream

# 3. Probar WebSocket (instalar websocat: cargo install websocat)
echo '{"type": "list_tools"}' | websocat ws://localhost:8000/ws
```

## **🔧 Herramientas disponibles**

1. **check_vehicle_safety** - Consulta NHTSA API
2. **llm_extract_vehicle_info** - Extrae info con Gemini LLM  
3. **generate_markdown_report** - Genera reportes
4. **send_email_smtp** - Envía emails con reportes

## **📞 Ejemplo de uso desde cliente:**

```json
{
  "type": "call_tool",
  "name": "check_vehicle_safety",
  "arguments": {
    "make": "BMW",
    "model": "Serie 3", 
    "year": 2020
  }
}
```

## **🔍 Transportes soportados:**

- ✅ **stdio**: Para clientes locales (Claude Desktop, VS Code)
- ✅ **HTTP**: Para clientes web y remotos  
- ✅ **SSE**: Streaming via Server-Sent Events
- ✅ **WebSocket**: Comunicación bidireccional en tiempo real