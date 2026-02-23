"""
Herramientas MCP específicas para el análisis de seguridad vehicular
Sistema Model Context Protocol - Práctica MCP
"""

import asyncio
import json
import logging
import os
import re
import smtplib
import tempfile
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def decode_vin_year(vin: str) -> Optional[int]:
    """
    Decode year from VIN (17-character Vehicle Identification Number)
    The 10th character represents the model year
    """
    if not vin or len(vin) != 17:
        return None
    
    year_code = vin[9].upper()
    
    # VIN year code mapping (10th character)
    year_codes = {
        'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
        'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
        'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
        'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
        'Y': 2030,
        # Numbers for older years
        '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005,
        '6': 2006, '7': 2007, '8': 2008, '9': 2009
    }
    
    return year_codes.get(year_code)

# MCP Tools for Vehicle Safety Analysis

async def check_vehicle_safety(make: str, model: str, year: Optional[int] = None, vin: Optional[str] = None) -> Dict[str, Any]:
    """
    Consulta recalls y calificaciones de seguridad de vehículos usando la API de NHTSA.
    
    Categoría: External API
    Función: Obtiene datos oficiales de seguridad vehicular del gobierno de EE.UU.
    """
    try:
        # Try to decode year from VIN if year not provided
        if not year and vin:
            vin_year = decode_vin_year(vin)
            if vin_year:
                year = vin_year
                logger.info(f"Year decoded from VIN: {year}")
        
        # BMW model mapping for NHTSA API compatibility
        if make.upper() == "BMW":
            bmw_model_mapping = {
                "serie 3": "330i",
                "series 3": "330i", 
                "3 series": "330i",
                "3-series": "330i",
                "serie3": "330i",
                "serie 5": "530i",
                "series 5": "530i",
                "5 series": "530i",
                "5-series": "530i",
                "serie5": "530i",
                "x3": "X3",
                "x5": "X5",
                "x1": "X1",
                "x7": "X7"
            }
            
            model_lower = model.lower().strip()
            if model_lower in bmw_model_mapping:
                original_model = model
                model = bmw_model_mapping[model_lower]
                logger.info(f"BMW model mapped: '{original_model}' -> '{model}'")
        
        # If no year is provided, try common recent years
        years_to_try = [year] if year else [2019, 2020, 2021, 2022, 2018]
        
        # Use the correct API endpoint
        recalls_base_url = "https://api.nhtsa.gov/recalls"
        safety_base_url = os.getenv("NHTSA_BASE_URL", "https://api.nhtsa.gov/SafetyRatings")
        
        # Initialize results
        recalls = []
        safety_ratings = {}
        successful_year = None
        
        async with httpx.AsyncClient() as client:
            # 1. Get vehicle recalls using the working endpoint
            for try_year in years_to_try:
                try:
                    recalls_url = f"{recalls_base_url}/recallsByVehicle"
                    params = {"make": make, "model": model}
                    if try_year:
                        params["modelYear"] = try_year
                    
                    logger.info(f"Searching recalls: {recalls_url} with params: {params}")
                    response = await client.get(recalls_url, params=params, timeout=30)
                    response.raise_for_status()
                    
                    recalls_data = response.json()
                    results = recalls_data.get("results", [])
                    
                    logger.info(f"API response: Found {len(results)} recalls for year {try_year}")
                    
                    if len(results) > 0:
                        successful_year = try_year
                        for recall in results:
                            recalls.append({
                                "campaign_number": recall.get("NHTSACampaignNumber", "N/A"),
                                "manufacturer": recall.get("Manufacturer", "N/A"),
                                "component": recall.get("Component", "N/A"),
                                "summary": recall.get("Summary", "N/A"),
                                "consequence": recall.get("Consequence", "N/A"),
                                "remedy": recall.get("Remedy", "N/A"),
                                "date": recall.get("ReportReceivedDate", "N/A"),
                                "park_it": recall.get("parkIt", False),
                                "park_outside": recall.get("parkOutSide", False)
                            })
                        
                        logger.info(f"Found {len(recalls)} recalls for {make} {model} {try_year}")
                        break  # Stop trying other years if we found results
                    
                except Exception as e:
                    logger.warning(f"Error fetching recalls for year {try_year}: {e}")
                    continue
                
                # Try alternative model formats if main search fails
                if len(recalls) == 0:
                    alternative_models = []
                    
                    # Try common model variations
                    if "serie" in model.lower() or "series" in model.lower():
                        # BMW Serie 3 -> 3 Series, BMW 3-Series, BMW 3
                        base_num = ''.join(filter(str.isdigit, model))
                        if base_num:
                            alternative_models.extend([
                                f"{base_num} Series",
                                f"{base_num}-Series", 
                                base_num
                            ])
                    
                    # Try with spaces, hyphens, etc.
                    alternative_models.extend([
                        model.replace(" ", ""),
                        model.replace(" ", "-"),
                        model.replace("-", " "),
                        model.upper(),
                        model.lower(),
                        model.title()
                    ])
                    
                    for alt_model in alternative_models[:3]:  # Limit requests
                        try:
                            params = {"make": make, "model": alt_model}
                            if year:
                                params["modelYear"] = year
                            
                            logger.info(f"Trying alternative model: {alt_model}")
                            response = await client.get(recalls_url, params=params, timeout=30)
                            response.raise_for_status()
                            
                            recalls_data = response.json()
                            results = recalls_data.get("results", [])
                            
                            if len(results) > 0:
                                logger.info(f"Found {len(results)} recalls with alternative model: {alt_model}")
                                for recall in results:
                                    recalls.append({
                                        "campaign_number": recall.get("NHTSACampaignNumber", "N/A"),
                                        "manufacturer": recall.get("Manufacturer", "N/A"),
                                        "component": recall.get("Component", "N/A"),
                                        "summary": recall.get("Summary", "N/A"),
                                        "consequence": recall.get("Consequence", "N/A"),
                                        "remedy": recall.get("Remedy", "N/A"),
                                        "date": recall.get("ReportReceivedDate", "N/A"),
                                        "park_it": recall.get("parkIt", False),
                                        "park_outside": recall.get("parkOutSide", False)
                                    })
                                break  # Stop on first successful match
                                
                        except Exception as e:
                            logger.debug(f"Alternative model {alt_model} failed: {e}")
                            continue
            
            # 2. Get safety ratings
            try:
                if year:
                    safety_url = f"{safety_base_url}/vehicle/{year}/{make}/{model}"
                    response = await client.get(safety_url, timeout=30)
                    response.raise_for_status()
                    
                    safety_data = response.json()
                    results = safety_data.get("Results", [])
                    
                    if results:
                        first_result = results[0]
                        safety_ratings = {
                            "overall_rating": first_result.get("OverallRating"),
                            "frontal_crash": first_result.get("FrontalCrashRating"),
                            "side_crash": first_result.get("SideCrashRating"),
                            "rollover": first_result.get("RolloverRating")
                        }
                
                logger.info(f"Safety ratings obtained for {make} {model} {year}")
                
            except Exception as e:
                logger.warning(f"Error fetching safety ratings: {e}")
                safety_ratings = {}
        
        # Generate recommendations
        recommendations = []
        if recalls:
            recommendations.append("Verificar que todos los recalls hayan sido atendidos antes de la compra")
            recommendations.append("Solicitar documentación de reparaciones de recalls completados")
        else:
            recommendations.append("No se encontraron recalls activos para este modelo")
        
        if safety_ratings.get("overall_rating"):
            rating = safety_ratings["overall_rating"]
            if rating in ["4", "5"]:
                recommendations.append(f"Excelente calificación de seguridad ({rating} estrellas)")
            elif rating in ["2", "3"]:
                recommendations.append(f"Calificación de seguridad moderada ({rating} estrellas)")
            else:
                recommendations.append("Considerar opciones con mejor calificación de seguridad")
        
        # Prepare result
        vehicle_data = {
            "make": make,
            "model": model,
            "year": successful_year or year,  # Use the year that worked, or original year
            "vin": vin,
            "recalls": recalls,
            "safety_ratings": safety_ratings,
            "total_recalls": len(recalls),
            "year_used": successful_year  # Show which year was actually used for the search
        }
        
        return {
            "success": True,
            "data": vehicle_data,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error in check_vehicle_safety: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def llm_extract_vehicle_info(text: str) -> Dict[str, Any]:
    """
    Extrae información de vehículos (marca, modelo, año, VIN) de texto en lenguaje natural usando Gemini.
    
    Categoría: LLM Processing
    Función: Procesamiento inteligente de texto con Google Gemini únicamente
    """
    try:
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not gemini_key:
            return {
                "success": False,
                "error": "GOOGLE_API_KEY not found in environment variables"
            }
        
        result = await _extract_with_gemini(text, gemini_key)
        if result["success"]:
            logger.info("Vehicle info extracted using Google Gemini")
            return result
        else:
            return {
                "success": False,
                "error": f"Gemini extraction failed: {result.get('error', 'Unknown error')}"
            }
        
    except Exception as e:
        logger.error(f"Error in llm_extract_vehicle_info: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def _extract_with_gemini(text: str, api_key: str) -> Dict[str, Any]:
    """Extract vehicle info using Google Gemini"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # Try different models in order of preference
        models_to_try = [
            'models/gemini-2.5-flash',
            'models/gemini-2.0-flash', 
            'models/gemini-flash-latest',
            'models/gemini-pro-latest'
        ]
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                
                prompt = f"""
                Analiza el siguiente texto y extrae la información del vehículo.
                
                IMPORTANTE para BMW: 
                - Si detectas "BMW Serie 3" o "BMW Series 3", usar modelo "Serie 3"
                - Si detectas "BMW Serie 5" o "BMW Series 5", usar modelo "Serie 5"
                - Mantener el formato original del usuario
                
                Devuelve ÚNICAMENTE un objeto JSON válido con estos campos exactos:
                {{
                    "make": "marca del vehículo (string)",
                    "model": "modelo del vehículo (string exactamente como aparece)", 
                    "year": año del modelo (número entero o null),
                    "vin": "número VIN si está presente (string o null)"
                }}
                
                Texto a analizar: {text}
                
                Responde SOLO con el JSON, sin texto adicional.
                """
                
                response = model.generate_content(prompt)
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    
                    # Validate required fields
                    if data.get("make") and data.get("model"):
                        logger.info(f"Successfully used Gemini model: {model_name}")
                        return {"success": True, "data": data}
                    else:
                        return {"success": False, "error": "Missing required fields in Gemini response"}
                else:
                    return {"success": False, "error": "No valid JSON found in Gemini response"}
                    
            except Exception as model_error:
                logger.warning(f"Model {model_name} failed: {model_error}")
                if model_name == models_to_try[-1]:  # Last model
                    raise model_error
                continue
        
        return {"success": False, "error": "All Gemini models failed"}
            
    except Exception as e:
        return {"success": False, "error": f"Gemini extraction failed: {e}"}

async def send_email_smtp(to_email: str, subject: str, body: str, attachment_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Envía notificaciones por email con soporte para adjuntos.
    
    Categoría: Real Action
    Función: Envío real de emails o simulación para desarrollo
    """
    try:
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "1025"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("EMAIL_FROM", "vehicle-safety@mcp.local")
        
        # Real email sending
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    
                    filename = Path(attachment_path).name
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
                
                logger.info(f"Attachment added: {filename}")
            
            # Send email
            if smtp_username and smtp_password:
                server.starttls()
                server.login(smtp_username, smtp_password)
            
            server.sendmail(from_email, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            
            return {
                "success": True,
                "message": f"Email enviado exitosamente a {to_email}",
                "details": {
                    "to": to_email,
                    "subject": subject,
                    "attachment": attachment_path is not None
                }
            }
            
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def generate_markdown_report(title: str, content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Genera reportes de seguridad vehicular en formato Markdown.
    
    Categoría: Content Generation  
    Función: Creación de documentos estructurados
    """
    try:
        # Create output directory
        output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs"))
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\-_]', '_', title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        filepath = output_dir / filename
        
        # Prepare markdown content
        markdown_content = f"# {title}\n\n"
        
        # Add metadata if provided
        if metadata:
            markdown_content += "## Información del Vehículo\n\n"
            for key, value in metadata.items():
                if value is not None:
                    markdown_content += f"- **{key.title()}**: {value}\n"
            markdown_content += "\n"
        
        # Add generation timestamp
        markdown_content += f"**Generado**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_content += "---\n\n"
        
        # Add main content
        markdown_content += content
        
        # Add footer
        markdown_content += "\n\n---\n"
        markdown_content += "*Reporte generado por el Sistema MCP de Análisis de Seguridad Vehicular*\n"
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        file_size = filepath.stat().st_size
        
        logger.info(f"Markdown report generated: {filepath} ({file_size} bytes)")
        
        return {
            "success": True,
            "path": str(filepath),
            "filename": filename,
            "size": file_size,
            "content_length": len(content)
        }
        
    except Exception as e:
        logger.error(f"Error generating markdown report: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# MCP Tools Dictionary
mcp_tools_dict = {
    "check_vehicle_safety": check_vehicle_safety,
    "llm_extract_vehicle_info": llm_extract_vehicle_info, 
    "send_email_smtp": send_email_smtp,
    "generate_markdown_report": generate_markdown_report
}

# Tool descriptions for MCP protocol
mcp_tools_descriptions = {
    "check_vehicle_safety": "Consulta recalls y calificaciones de seguridad de NHTSA para un vehículo específico",
    "llm_extract_vehicle_info": "Extrae información de vehículos de texto natural usando LLM con fallbacks",
    "send_email_smtp": "Envía notificaciones por email con soporte para adjuntos", 
    "generate_markdown_report": "Genera reportes de seguridad vehicular en formato Markdown"
}

def format_mcp_tool_output(tool_name: str, result: Dict[str, Any]) -> str:
    """Format tool output for MCP protocol"""
    
    if tool_name == "check_vehicle_safety":
        if result.get("success"):
            data = result["data"]
            vehicle_info = f"{data['make']} {data['model']} {data.get('year', 'N/A')}"
            recall_count = len(data.get("recalls", []))
            rating = data.get("safety_ratings", {}).get("overall_rating", "N/A")
            
            output = f"🚗 **Vehículo**: {vehicle_info}\n"
            output += f"📋 **Recalls**: {recall_count} encontrados\n"
            output += f"⭐ **Calificación**: {rating} estrellas\n\n"
            
            if data.get("recalls"):
                output += "**Recalls encontrados:**\n"
                for i, recall in enumerate(data["recalls"][:3], 1):
                    output += f"{i}. {recall.get('component', 'N/A')} - {recall.get('summary', 'N/A')[:100]}...\n"
            
            return output
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"
    
    elif tool_name == "llm_extract_vehicle_info":
        if result.get("success"):
            data = result["data"]
            return f"✅ **Información extraída**:\n- Marca: {data.get('make')}\n- Modelo: {data.get('model')}\n- Año: {data.get('year', 'N/A')}\n- VIN: {data.get('vin', 'N/A')}"
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"
    
    elif tool_name == "send_email_smtp":
        if result.get("success"):
            return f"📧 {result.get('message', 'Email enviado exitosamente')}"
        else:
            return f"❌ Error enviando email: {result.get('error', 'Unknown error')}"
    
    elif tool_name == "generate_markdown_report":
        if result.get("success"):
            return f"📄 **Reporte generado**: {result.get('filename')}\n📁 **Ruta**: {result.get('path')}\n💾 **Tamaño**: {result.get('size', 0)} bytes"
        else:
            return f"❌ Error generando reporte: {result.get('error', 'Unknown error')}"
    
    # Default formatting
    return json.dumps(result, indent=2, ensure_ascii=False)

__all__ = [
    "check_vehicle_safety",
    "llm_extract_vehicle_info", 
    "send_email_smtp",
    "generate_markdown_report",
    "mcp_tools_dict",
    "mcp_tools_descriptions",
    "format_mcp_tool_output"
]