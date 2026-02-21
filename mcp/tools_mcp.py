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
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Tools for Vehicle Safety Analysis

async def check_vehicle_safety(make: str, model: str, year: Optional[int] = None, vin: Optional[str] = None) -> Dict[str, Any]:
    """
    Consulta recalls y calificaciones de seguridad de vehículos usando la API de NHTSA.
    
    Categoría: External API
    Función: Obtiene datos oficiales de seguridad vehicular del gobierno de EE.UU.
    """
    try:
        # Use the correct API endpoint
        recalls_base_url = "https://api.nhtsa.gov/recalls"
        safety_base_url = os.getenv("NHTSA_BASE_URL", "https://api.nhtsa.gov/SafetyRatings")
        
        # Initialize results
        recalls = []
        safety_ratings = {}
        
        async with httpx.AsyncClient() as client:
            # 1. Get vehicle recalls using the working endpoint
            try:
                recalls_url = f"{recalls_base_url}/recallsByVehicle"
                params = {"make": make, "model": model}
                if year:
                    params["modelYear"] = year
                
                logger.info(f"Searching recalls: {recalls_url} with params: {params}")
                response = await client.get(recalls_url, params=params, timeout=30)
                response.raise_for_status()
                
                recalls_data = response.json()
                results = recalls_data.get("results", [])
                
                logger.info(f"API response: Found {len(results)} recalls")
                
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
                
                logger.info(f"Found {len(recalls)} recalls for {make} {model} {year or 'all years'}")
                
            except Exception as e:
                logger.warning(f"Error fetching recalls: {e}")
                
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
            "year": year,
            "vin": vin,
            "recalls": recalls,
            "safety_ratings": safety_ratings,
            "total_recalls": len(recalls)
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
    Extrae información de vehículos (marca, modelo, año, VIN) de texto en lenguaje natural usando LLM.
    
    Categoría: LLM Processing
    Función: Procesamiento inteligente de texto con múltiples proveedores LLM y fallback
    """
    try:
        # Try multiple LLM providers with fallbacks
        
        # 1. Try Google Gemini first
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            result = await _extract_with_gemini(text, gemini_key)
            if result["success"]:
                logger.info("Vehicle info extracted using Gemini")
                return result
        
        # 2. Fallback to OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            result = await _extract_with_openai(text, openai_key)
            if result["success"]:
                logger.info("Vehicle info extracted using OpenAI")
                return result
        
        # 3. Final fallback to regex
        result = await _extract_with_regex(text)
        if result["success"]:
            logger.info("Vehicle info extracted using regex fallback")
            return result
        
        return {
            "success": False,
            "error": "Could not extract vehicle information from text"
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
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Analiza el siguiente texto y extrae la información del vehículo.
        Devuelve ÚNICAMENTE un objeto JSON válido con estos campos exactos:
        {{
            "make": "marca del vehículo (string)",
            "model": "modelo del vehículo (string)", 
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
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": "Missing required fields in Gemini response"}
        else:
            return {"success": False, "error": "No valid JSON found in Gemini response"}
            
    except Exception as e:
        return {"success": False, "error": f"Gemini extraction failed: {e}"}

async def _extract_with_openai(text: str, api_key: str) -> Dict[str, Any]:
    """Extract vehicle info using OpenAI"""
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                Extract vehicle information from this text: "{text}"
                
                Return only a JSON object with:
                {{"make": "brand", "model": "model name", "year": year_number_or_null, "vin": "vin_or_null"}}
                """
            }],
            max_tokens=150,
            temperature=0
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            if data.get("make") and data.get("model"):
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": "Missing required fields in OpenAI response"}
        else:
            return {"success": False, "error": "No valid JSON in OpenAI response"}
            
    except Exception as e:
        return {"success": False, "error": f"OpenAI extraction failed: {e}"}

async def _extract_with_regex(text: str) -> Dict[str, Any]:
    """Fallback regex-based extraction"""
    try:
        # Extract year (4 digits between 1990-2030)
        year_match = re.search(r'\b(199\d|20[0-2]\d|2030)\b', text)
        year = int(year_match.group(0)) if year_match else None
        
        # Extract VIN (17 alphanumeric characters)
        vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', text, re.IGNORECASE)
        vin = vin_match.group(0) if vin_match else None
        
        # Clean text and extract make/model
        # Remove common Spanish phrases first
        clean_text = re.sub(r'(?i)\b(?:quiero|necesito|dime|dame|consulta|verificar|revisar|seguridad|recalls?|información|análisis|de|del|la|el|un|una|¿qué|qué|tiene|sobre|saber)\b', ' ', text)
        
        # Remove year and VIN from text
        if year:
            clean_text = re.sub(r'\b' + str(year) + r'\b', '', clean_text)
        if vin:
            clean_text = re.sub(r'\b' + re.escape(vin) + r'\b', '', clean_text, flags=re.IGNORECASE)
        
        # Remove punctuation and normalize
        clean_text = re.sub(r'[¿?¡!.,;:]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Define known car manufacturers and models
        known_makes = {
            'bmw': 'BMW',
            'toyota': 'Toyota', 
            'ford': 'Ford',
            'chevrolet': 'Chevrolet',
            'honda': 'Honda',
            'nissan': 'Nissan',
            'jeep': 'Jeep',
            'chrysler': 'Chrysler',
            'dodge': 'Dodge',
            'mercedes': 'Mercedes-Benz',
            'audi': 'Audi',
            'volkswagen': 'Volkswagen',
            'hyundai': 'Hyundai',
            'kia': 'Kia',
            'mazda': 'Mazda',
            'subaru': 'Subaru',
            'mitsubishi': 'Mitsubishi'
        }
        
        # BMW specific model mapping
        bmw_models = {
            'serie 3': '330i',
            'series 3': '330i', 
            '3 series': '330i',
            '3-series': '330i',
            'serie 5': '530i',
            'series 5': '530i',
            'x3': 'X3',
            'x5': 'X5'
        }
        
        # Try to find manufacturer and model
        make = None
        model = None
        
        # Split into words for analysis
        words = clean_text.lower().split()
        
        # Find manufacturer
        for i, word in enumerate(words):
            if word in known_makes:
                make = known_makes[word]
                # Look for model after the make
                remaining_words = words[i+1:]
                
                if make == 'BMW':
                    # Special handling for BMW
                    model_text = ' '.join(remaining_words).strip()
                    
                    # Check for known BMW model patterns
                    for bmw_pattern, bmw_replacement in bmw_models.items():
                        if bmw_pattern in model_text:
                            model = bmw_replacement
                            break
                    
                    # If no specific model found, try to extract numbers
                    if not model:
                        number_match = re.search(r'\b(\d)\b', model_text)
                        if number_match:
                            num = number_match.group(1)
                            model = f"{num}30i"  # Default to 330i, 530i, etc.
                        else:
                            model = "330i"  # Default fallback
                    
                elif len(remaining_words) > 0:
                    # For other manufacturers, take the next words as model
                    model_parts = []
                    for word in remaining_words:
                        if word not in ['recalls', 'recall', 'safety', 'seguridad', 'information']:
                            model_parts.append(word.title())
                        else:
                            break
                    model = ' '.join(model_parts[:3]) if model_parts else None  # Limit to 3 words
                
                break
        
        # If manufacturer not found by name, try common patterns
        if not make:
            # Try patterns like "Toyota Corolla", "Ford F-150"
            pattern_match = re.search(r'\b(BMW|Toyota|Ford|Chevrolet|Honda|Nissan|Jeep|Mercedes|Audi)\s+([A-Za-z0-9\-]+)', clean_text, re.IGNORECASE)
            if pattern_match:
                make = pattern_match.group(1).title()
                model = pattern_match.group(2)
                
                # Special BMW handling
                if make.upper() == 'BMW':
                    model_lower = model.lower()
                    if model_lower in bmw_models:
                        model = bmw_models[model_lower]
                    elif re.match(r'\d', model):
                        # If it starts with a number, add 30i
                        model = f"{model[0]}30i"
        
        # Final validation and cleanup
        if make and model:
            # Clean up model name
            model = re.sub(r'[^\w\s\-]', '', model).strip()
            if not model:
                model = "Unknown"
                
            return {
                "success": True,
                "data": {
                    "make": make,
                    "model": model,
                    "year": year,
                    "vin": vin
                }
            }
        else:
            return {"success": False, "error": "Could not extract vehicle make and model from text"}
            
    except Exception as e:
        return {"success": False, "error": f"Regex extraction failed: {e}"}

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
        
        # Simulation mode for development
        if smtp_host == "localhost" and smtp_port == 1025:
            logger.info(f"SIMULATION MODE: Email would be sent to {to_email}")
            return {
                "success": True,
                "message": f"Email simulado enviado a {to_email} (modo desarrollo)",
                "details": {
                    "to": to_email,
                    "subject": subject,
                    "body_length": len(body),
                    "attachment": attachment_path is not None
                }
            }
        
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

async def web_fetch(url: str) -> Dict[str, Any]:
    """
    Obtiene y procesa contenido web para análisis adicional.
    
    Categoría: External Resource
    Función: Web scraping y procesamiento de contenido HTML
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30, headers={
                "User-Agent": "MCP Vehicle Safety Analysis Bot 1.0"
            })
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text()
            
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Extract title
            title = soup.title.string if soup.title else "No title"
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "")
            
            logger.info(f"Web content fetched from {url} ({len(text_content)} chars)")
            
            return {
                "success": True,
                "data": {
                    "url": url,
                    "title": title.strip(),
                    "description": meta_desc.strip(),
                    "content": text_content,
                    "content_length": len(text_content),
                    "status_code": response.status_code
                }
            }
            
    except Exception as e:
        logger.error(f"Error fetching web content from {url}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# MCP Tools Dictionary
mcp_tools_dict = {
    "check_vehicle_safety": check_vehicle_safety,
    "llm_extract_vehicle_info": llm_extract_vehicle_info, 
    "send_email_smtp": send_email_smtp,
    "generate_markdown_report": generate_markdown_report,
    "web_fetch": web_fetch
}

# Tool descriptions for MCP protocol
mcp_tools_descriptions = {
    "check_vehicle_safety": "Consulta recalls y calificaciones de seguridad de NHTSA para un vehículo específico",
    "llm_extract_vehicle_info": "Extrae información de vehículos de texto natural usando LLM con fallbacks",
    "send_email_smtp": "Envía notificaciones por email con soporte para adjuntos", 
    "generate_markdown_report": "Genera reportes de seguridad vehicular en formato Markdown",
    "web_fetch": "Obtiene y procesa contenido web para análisis adicional"
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
    
    elif tool_name == "web_fetch":
        if result.get("success"):
            data = result["data"]
            return f"🌐 **Contenido obtenido de**: {data.get('url')}\n📰 **Título**: {data.get('title')}\n📝 **Contenido**: {data.get('content_length', 0)} caracteres"
        else:
            return f"❌ Error obteniendo contenido web: {result.get('error', 'Unknown error')}"
    
    # Default formatting
    return json.dumps(result, indent=2, ensure_ascii=False)

# Export all MCP tools and utilities
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