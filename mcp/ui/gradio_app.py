"""
Interfaz Gradio para el sistema MCP de análisis de vehículos
Permite consultas de seguridad, generación de reportes y envío de emails
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

import gradio as gr

# Load environment variables from the correct path
# Get the project root (three levels up from mcp/ui/gradio_app.py)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Import MCP agent
try:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from agents.langgraph_adapter import VehicleSafetyAgent, MCPClient
except ImportError as e:
    # Fallback if agents module not available
    logger.warning(f"Could not import MCP agent: {e}. Running in basic mode.")
    VehicleSafetyAgent = None
    MCPClient = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleSafetyUI:
    """Gradio UI for vehicle safety analysis"""
    
    def __init__(self, mcp_base_url: str = "http://localhost:8000", mcp_token: str = "default-token"):
        self.mcp_base_url = mcp_base_url
        self.mcp_token = mcp_token
        self.agent = None
        self.mcp_client = None
        
        # Initialize MCP connections
        if VehicleSafetyAgent:
            self.agent = VehicleSafetyAgent(mcp_base_url, mcp_token)
        if MCPClient:
            self.mcp_client = MCPClient(mcp_base_url, mcp_token)
        
        # Create output directory
        self.output_dir = Path("./out")
        self.output_dir.mkdir(exist_ok=True)
    
    async def analyze_vehicle_safety(
        self, 
        user_text: str = "", 
        make: str = "", 
        model: str = "", 
        year: Optional[int] = None,
        vin: str = "",
        email: str = ""
    ) -> Tuple[str, Optional[str]]:
        """
        Analyze vehicle safety using MCP tools
        Returns: (results_text, download_file_path)
        """
        
        try:
            # If we have the agent, use the full workflow
            if self.agent and user_text.strip():
                logger.info(f"Running full analysis for: {user_text}")
                result = await self.agent.run_analysis(user_text, email)  # Pass email to agent
                
                if result.get("success"):
                    extracted = result.get("extracted_info", {})
                    safety_report = result.get("safety_report", {})
                    markdown_path = result.get("markdown_path")
                    
                    # Format results for display
                    results_text = self._format_safety_results(safety_report)
                    
                    return results_text, markdown_path
                else:
                    return "", None
            
            # Fallback: use individual MCP calls
            elif self.mcp_client:
                # Use provided fields or extract from text
                if user_text.strip() and not (make and model):
                    extract_result = await self.mcp_client.call_tool(
                        "llm_extract_vehicle_info", 
                        {"text": user_text}
                    )
                    
                    if extract_result.get("success"):
                        data = extract_result.get("data", {})
                        make = make or data.get("make", "")
                        model = model or data.get("model", "")
                        year = year or data.get("year")
                        vin = vin or data.get("vin", "")
                
                if not (make and model):
                    return "", None
                
                # Check vehicle safety
                safety_result = await self.mcp_client.call_tool(
                    "check_vehicle_safety",
                    {
                        "make": make,
                        "model": model,
                        "year": year,
                        "vin": vin if vin else None
                    }
                )
                
                if not safety_result.get("success"):
                    return "", None
                
                # Format results
                results_text = self._format_safety_results(safety_result)
                
                # Generate report if requested
                report_path = None
                if safety_result.get("success"):
                    report_result = await self._generate_report_mcp(safety_result, make, model, year)
                    if report_result.get("success"):
                        report_path = report_result.get("path")
                
                return results_text, report_path
            
            else:
                return "", None
                
        except Exception as e:
            logger.error(f"Error in vehicle analysis: {e}")
            return "", None
    
    def _format_safety_results(self, safety_result: dict) -> str:
        """Format safety results for display"""
        if not safety_result or not safety_result.get("success"):
            return "No se pudieron obtener datos de seguridad"
        
        data = safety_result.get("data", {})
        
        # Vehicle info
        text = f"# 🚗 {data.get('make')} {data.get('model')} ({data.get('year') or 'Año no especificado'})\n\n"
        
        # Recalls section
        recalls = data.get("recalls", [])
        text += f"## 📋 Recalls Encontrados: {len(recalls)}\n\n"
        
        if recalls:
            for i, recall in enumerate(recalls, 1):
                text += f"### Recall #{i}\n"
                text += f"**Campaña:** {recall.get('campaign_number', 'N/A')}\n\n"
                text += f"**Componente:** {recall.get('component', 'N/A')}\n\n"
                text += f"**Resumen:** {recall.get('summary', 'N/A')}\n\n"
                text += f"**Consecuencia:** {recall.get('consequence', 'N/A')}\n\n"
                text += f"**Remedio:** {recall.get('remedy', 'N/A')}\n\n"
                text += f"**Fecha:** {recall.get('date', 'N/A')}\n\n"
                text += "---\n\n"
        else:
            text += "✅ No se encontraron recalls registrados para este vehículo.\n\n"
        
        # Safety ratings
        safety_ratings = data.get("safety_ratings", {})
        if safety_ratings and any(safety_ratings.values()):
            text += "## ⭐ Calificaciones de Seguridad (NHTSA)\n\n"
            text += f"- **Calificación General:** {safety_ratings.get('overall_rating', 'N/A')}\n"
            text += f"- **Choque Frontal:** {safety_ratings.get('frontal_crash', 'N/A')}\n"
            text += f"- **Choque Lateral:** {safety_ratings.get('side_crash', 'N/A')}\n"
            text += f"- **Vuelco:** {safety_ratings.get('rollover', 'N/A')}\n\n"
        
        # Recommendations
        recommendations = safety_result.get("recommendations", [])
        if recommendations:
            text += "## 💡 Recomendaciones\n\n"
            for rec in recommendations:
                text += f"- {rec}\n"
        
        return text
    
    async def _generate_report_mcp(self, safety_result: dict, make: str, model: str, year: Optional[int]) -> dict:
        """Generate markdown report using MCP"""
        if not self.mcp_client:
            return {"success": False, "error": "MCP client not available"}
        
        title = f"Reporte de Seguridad - {make} {model} {year or 'sin año'}"
        content = self._format_safety_results(safety_result)
        
        return await self.mcp_client.call_tool(
            "generate_markdown_report",
            {"title": title, "content": content}
        )
    
    def create_interface(self):
        """Create and return the Gradio interface"""
        
        with gr.Blocks(
            title="🚗 Análisis de Seguridad Vehicular - MCP",
            theme=gr.themes.Soft()
        ) as demo:
            
            gr.Markdown("""
            # 🚗 Sistema de Análisis de Seguridad Vehicular
            
            **Powered by MCP (Model Context Protocol)**
            
            Este sistema utiliza múltiples herramientas MCP para:
            - 🔍 Extraer información de vehículos con LLM
            - 📊 Consultar recalls y calificaciones de seguridad (NHTSA)
            - 📄 Generar reportes en formato Markdown
            - 📧 Enviar notificaciones por email
            """)
            
            with gr.Tab("🔍 Consulta por Texto Libre"):
                gr.Markdown("Escribe tu consulta en lenguaje natural y el sistema extraerá la información automáticamente.")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        user_text_input = gr.Textbox(
                            label="Consulta de seguridad",
                            placeholder="Ejemplo: 'Dime la seguridad de BMW Serie 3 2020' o '¿Qué recalls tiene Toyota Corolla?'",
                            lines=3
                        )
                        
                        email_input1 = gr.Textbox(
                            label="Email para notificación (opcional)",
                            placeholder="tu@email.com"
                        )
                        
                        analyze_btn1 = gr.Button("🔍 Analizar Seguridad", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Ejemplos de consultas:")
                        gr.Markdown("""
                        - "Dime la seguridad de BMW Serie 3 2020"
                        - "¿Qué recalls tiene Toyota Corolla 2018?"
                        - "VIN 1HGCM82633A004352 Ford Focus"
                        - "Revisa seguridad Honda Civic"
                        """)
            
            with gr.Tab("📝 Consulta por Campos"):
                gr.Markdown("Completa los campos manualmente para una consulta específica.")
                
                with gr.Row():
                    with gr.Column():
                        make_input = gr.Textbox(label="Marca", placeholder="BMW, Toyota, Ford...")
                        model_input = gr.Textbox(label="Modelo", placeholder="Serie 3, Corolla, Focus...")
                    
                    with gr.Column():
                        year_input = gr.Number(label="Año", precision=2020, minimum=1990, maximum=2025)
                        vin_input = gr.Textbox(label="VIN (opcional)", placeholder="17 caracteres")
                
                email_input2 = gr.Textbox(
                    label="Email para notificación (opcional)",
                    placeholder="tu@email.com"
                )
                
                analyze_btn2 = gr.Button("🔍 Analizar Seguridad", variant="primary", size="lg")
            
            # Results section (shared between tabs)
            gr.Markdown("---")
            gr.Markdown("## 📊 Resultados del Análisis")
            
            with gr.Row():
                with gr.Column(scale=2):
                    results_display = gr.Markdown(
                        label="Resultados",
                        value="Los resultados aparecerán aquí...",
                        height=400
                    )
                
                with gr.Column(scale=1):
                    download_file = gr.File(
                        label="📄 Descargar Reporte",
                        visible=False
                    )
            
            # Event handlers
            def sync_analyze_text(user_text, email):
                return asyncio.run(self.analyze_vehicle_safety(user_text=user_text, email=email))
            
            def sync_analyze_fields(make, model, year, vin, email):
                return asyncio.run(self.analyze_vehicle_safety(
                    make=make, model=model, year=year, vin=vin, email=email
                ))
            
            analyze_btn1.click(
                fn=sync_analyze_text,
                inputs=[user_text_input, email_input1],
                outputs=[results_display, download_file]
            ).then(
                fn=lambda x: gr.update(visible=bool(x)),
                inputs=[download_file],
                outputs=[download_file]
            )
            
            analyze_btn2.click(
                fn=sync_analyze_fields,
                inputs=[make_input, model_input, year_input, vin_input, email_input2],
                outputs=[results_display, download_file]
            ).then(
                fn=lambda x: gr.update(visible=bool(x)),
                inputs=[download_file],
                outputs=[download_file]
            )

        
        return demo
    
    async def close(self):
        """Close connections"""
        if self.agent:
            await self.agent.close()
        if self.mcp_client:
            await self.mcp_client.close()

def main():
    """Main entry point for the Gradio app"""
    import os
    
    # Configuration
    MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    MCP_TOKEN = os.getenv("MCP_TOKEN", "default-token")
    
    # Create UI
    ui = VehicleSafetyUI(MCP_BASE_URL, MCP_TOKEN)
    demo = ui.create_interface()
    
    # Launch
    print(f"🚀 Starting Vehicle Safety UI...")
    print(f"📡 MCP Server: {MCP_BASE_URL}")
    print(f"🔑 Token: {MCP_TOKEN[:8]}...")
    
    # Find available port
    import socket
    def find_free_port(start_port=7860, max_port=7870):
        for port in range(start_port, max_port + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        return None
    
    port = find_free_port()
    if not port:
        print("❌ No se pudo encontrar un puerto disponible")
        return
    
    print(f"🌐 Starting Gradio on port {port}")
    
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False,
            show_error=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        # Cleanup
        asyncio.run(ui.close())

if __name__ == "__main__":
    main()