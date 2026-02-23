"""
LangGraph Adapter para MCP Server
Permite usar tools MCP dentro de workflows LangGraph
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict, Annotated

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Import MCP tools for fallback
try:
    from tools_mcp import mcp_tools_dict
except ImportError:
    from ..tools_mcp import mcp_tools_dict

# Try to import LangGraph components
HAS_LANGGRAPH = True
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor, ToolInvocation
except ImportError:
    HAS_LANGGRAPH = False
    # Only show warning when actually trying to use LangGraph
    pass

logger = logging.getLogger(__name__)

class MCPToolCall(BaseModel):
    """MCP tool call representation"""
    name: str
    arguments: Dict[str, Any]

class MCPClient:
    """Client for MCP Server HTTP transport"""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: str = "default-token"):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def _get_session(self):
        """Get a fresh HTTP session for each request"""
        return httpx.AsyncClient(timeout=30.0)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        try:
            async with await self._get_session() as client:
                response = await client.get(
                    f"{self.base_url}/tools",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                return data.get("tools", [])
        except Exception as e:
            logger.error(f"Error listing MCP tools: {e}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        try:
            payload = {"name": name, "arguments": arguments}
            async with await self._get_session() as client:
                response = await client.post(
                    f"{self.base_url}/call-tool",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("success"):
                    # Extract text content from MCP response
                    content = data.get("content", [])
                    if content and isinstance(content[0], dict):
                        text_content = content[0].get("text", "{}")
                        try:
                            return json.loads(text_content)
                        except json.JSONDecodeError:
                            return {"success": True, "result": text_content}
                    return {"success": True, "result": "Tool executed successfully"}
                else:
                    return {"success": False, "error": data.get("error", "Unknown error")}
                    
        except Exception as e:
            logger.error(f"Error calling MCP tool {name}: {e}")
            return {"success": False, "error": str(e)}

class MCPLangChainTool(BaseTool):
    """LangChain tool wrapper for MCP tools"""
    
    name: str
    description: str
    mcp_client: MCPClient
    mcp_tool_name: str
    
    def __init__(self, mcp_client: MCPClient, tool_def: Dict[str, Any]):
        self.mcp_client = mcp_client
        self.mcp_tool_name = tool_def["name"]
        
        super().__init__(
            name=tool_def["name"],
            description=tool_def["description"]
        )
    
    def _run(self, **kwargs) -> str:
        """Synchronous run (calls async version)"""
        try:
            # Check if we're already in an async context
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop
                loop = None
            
            if loop is None:
                # No running loop, safe to use asyncio.run()
                return asyncio.run(self._arun(**kwargs))
            else:
                # We're in an async context, create a task
                task = asyncio.create_task(self._arun(**kwargs))
                # This will be handled by the existing loop
                return asyncio.run_coroutine_threadsafe(
                    self._arun(**kwargs), 
                    loop
                ).result(timeout=30)
        except Exception as e:
            logger.error(f"Error in _run: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    async def _arun(self, **kwargs) -> str:
        """Run the MCP tool asynchronously"""
        try:
            result = await self.mcp_client.call_tool(self.mcp_tool_name, kwargs)
            
            # Ensure result is JSON serializable
            if hasattr(result, '__await__'):
                # If result is a coroutine, await it
                result = await result
            
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error in MCP tool {self.mcp_tool_name}: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

# LangGraph State
class AgentState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], "The messages in the conversation"]
    user_input: str
    extracted_info: Optional[Dict[str, Any]]
    safety_report: Optional[Dict[str, Any]]
    markdown_path: Optional[str]
    email_sent: Optional[bool]
    error: Optional[str]

class VehicleSafetyAgent:
    """Multi-step vehicle safety analysis agent using MCP tools"""
    
    def __init__(self, mcp_base_url: str = "http://localhost:8000", mcp_token: str = "default-token"):
        self.mcp_client = MCPClient(mcp_base_url, mcp_token)
        self.graph = None
        
        if HAS_LANGGRAPH:
            self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("extract_vehicle_info", self._extract_vehicle_info)
        workflow.add_node("check_safety", self._check_safety)
        workflow.add_node("generate_report", self._generate_report)
        workflow.add_node("send_email", self._send_email)
        
        # Add edges
        workflow.set_entry_point("extract_vehicle_info")
        workflow.add_edge("extract_vehicle_info", "check_safety")
        workflow.add_edge("check_safety", "generate_report")
        workflow.add_edge("generate_report", "send_email")
        workflow.add_edge("send_email", END)
        
        self.graph = workflow.compile()
    
    async def _extract_vehicle_info(self, state: AgentState) -> AgentState:
        """Extract vehicle information from user input"""
        logger.info("Extracting vehicle information...")
        
        result = await self.mcp_client.call_tool(
            "llm_extract_vehicle_info",
            {"text": state["user_input"]}
        )
        
        if result.get("success"):
            state["extracted_info"] = result.get("data")
        else:
            state["error"] = f"Could not extract vehicle info: {result.get('error')}"
        
        return state
    
    async def _check_safety(self, state: AgentState) -> AgentState:
        """Check vehicle safety using extracted information"""
        logger.info("Checking vehicle safety...")
        
        if not state.get("extracted_info"):
            state["error"] = "No vehicle information to check"
            return state
        
        info = state["extracted_info"]
        
        result = await self.mcp_client.call_tool(
            "check_vehicle_safety",
            {
                "make": info.get("make"),
                "model": info.get("model"),
                "year": info.get("year"),
                "vin": info.get("vin")
            }
        )
        
        if result.get("success"):
            state["safety_report"] = result
        else:
            state["error"] = f"Safety check failed: {result.get('error')}"
        
        return state
    
    async def _generate_report(self, state: AgentState) -> AgentState:
        """Generate markdown report"""
        logger.info("Generating markdown report...")
        
        if not state.get("safety_report"):
            state["error"] = "No safety report to generate"
            return state
        
        # Create report content
        report = state["safety_report"]
        data = report.get("data", {})
        
        title = f"Reporte de Seguridad - {data.get('make')} {data.get('model')} {data.get('year')}"
        
        content = f"""
## Información del Vehículo
- **Marca:** {data.get('make')}
- **Modelo:** {data.get('model')}
- **Año:** {data.get('year') or 'No especificado'}

## Recalls Encontrados
Total: {data.get('total_recalls', 0)}

"""
        
        recalls = data.get("recalls", [])
        if recalls:
            for i, recall in enumerate(recalls, 1):
                content += f"""
### Recall #{i}
- **Campaña:** {recall.get('campaign_number')}
- **Componente:** {recall.get('component')}
- **Resumen:** {recall.get('summary')}
- **Consecuencia:** {recall.get('consequence')}
- **Remedio:** {recall.get('remedy')}
- **Fecha:** {recall.get('date')}
"""
        else:
            content += "No se encontraron recalls registrados.\n"
        
        # Add safety ratings
        safety = data.get("safety_ratings", {})
        if safety:
            content += f"""
## Calificaciones de Seguridad
- **Calificación General:** {safety.get('overall_rating')}
- **Choque Frontal:** {safety.get('frontal_crash')}
- **Choque Lateral:** {safety.get('side_crash')}
- **Vuelco:** {safety.get('rollover')}
"""
        
        # Add recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            content += "\n## Recomendaciones\n"
            for rec in recommendations:
                content += f"- {rec}\n"
        
        # Generate the report
        result = await self.mcp_client.call_tool(
            "generate_markdown_report",
            {
                "title": title,
                "content": content
            }
        )
        
        if result.get("success"):
            state["markdown_path"] = result.get("path")
        else:
            state["error"] = f"Report generation failed: {result.get('error')}"
        
        return state
    
    async def _send_email(self, state: AgentState) -> AgentState:
        """Send email with report (only if email provided)"""
        logger.info("Checking if email should be sent...")
        
        # Only send email if user provided an email address
        user_email = state.get("user_email", "").strip()
        if not user_email:
            logger.info("No email provided - skipping email sending")
            state["email_sent"] = False
            state["email_status"] = "No email address provided - email not sent"
            return state
        
        if not state.get("markdown_path"):
            state["error"] = "No report to send"
            return state
        
        logger.info(f"Sending email to: {user_email}")
        
        subject = f"Reporte de Seguridad - {state['extracted_info'].get('make')} {state['extracted_info'].get('model')}"
        
        body = f"""
Hola,

Se ha generado un reporte de seguridad para el vehículo {state['extracted_info'].get('make')} {state['extracted_info'].get('model')}.

Reporte disponible en: {state['markdown_path']}

Total de recalls encontrados: {state['safety_report']['data'].get('total_recalls', 0)}

Saludos,
Sistema de Análisis de Vehículos
"""
        
        result = await self.mcp_client.call_tool(
            "send_email_smtp",
            {
                "to_email": user_email,  # Use actual user email
                "subject": subject,
                "body": body,
                "attachment_path": state.get("markdown_path")  # Attach the report
            }
        )
        
        if result.get("success"):
            state["email_sent"] = True
            state["email_status"] = f"Email sent successfully to {user_email}"
            logger.info(f"Email sent successfully to {user_email}")
        else:
            state["error"] = f"Email sending failed: {result.get('error')}"
            state["email_sent"] = False
            state["email_status"] = f"Email sending failed: {result.get('error')}"
        
        return state
    
    async def run_analysis(self, user_input: str, email: str = "") -> Dict[str, Any]:
        """Run complete vehicle safety analysis"""
        if not HAS_LANGGRAPH:
            # Fallback: run steps sequentially without LangGraph
            return await self._run_sequential_analysis(user_input, email)
        
        initial_state = {
            "messages": [],
            "user_input": user_input,
            "user_email": email.strip(),  # Add email to state
            "extracted_info": None,
            "safety_report": None,
            "markdown_path": None,
            "email_sent": False,
            "error": None
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return {
                "success": not bool(final_state.get("error")),
                "extracted_info": final_state.get("extracted_info"),
                "safety_report": final_state.get("safety_report"),
                "markdown_path": final_state.get("markdown_path"),
                "email_sent": final_state.get("email_sent"),
                "error": final_state.get("error")
            }
        except Exception as e:
            logger.error(f"Analysis workflow failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_sequential_analysis(self, user_input: str, email: str = "") -> Dict[str, Any]:
        """Fallback sequential analysis without LangGraph"""
        state = {
            "messages": [],
            "user_input": user_input,
            "user_email": email.strip(),  # Add email to state
            "extracted_info": None,
            "safety_report": None,
            "markdown_path": None,
            "email_sent": False,
            "error": None
        }
        
        try:
            # Run each step sequentially
            state = await self._extract_vehicle_info(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            state = await self._check_safety(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            state = await self._generate_report(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            state = await self._send_email(state)
            
            return {
                "success": not bool(state.get("error")),
                "extracted_info": state.get("extracted_info"),
                "safety_report": state.get("safety_report"),
                "markdown_path": state.get("markdown_path"),
                "email_sent": state.get("email_sent"),
                "error": state.get("error")
            }
            
        except Exception as e:
            logger.error(f"Sequential analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close MCP client connection"""
        # MCPClient now uses context managers, no explicit close needed
        pass

# Example usage function
async def example_usage():
    """Example of using the VehicleSafetyAgent"""
    agent = VehicleSafetyAgent()
    
    try:
        # Test analysis
        result = await agent.run_analysis("Dime la seguridad de BMW Serie 3 2020")
        print("Analysis Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(example_usage())