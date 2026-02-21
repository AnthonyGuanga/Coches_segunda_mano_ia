"""
Tests para las herramientas MCP del sistema de análisis vehicular
Incluye mocking de servicios externos y simulación de LLM
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
import tempfile
import os
from pathlib import Path

# Import MCP tools to test
import sys
sys.path.append(str(Path(__file__).parent.parent))

from tools_mcp import (
    check_vehicle_safety, 
    llm_extract_vehicle_info, 
    send_email_smtp,
    generate_markdown_report,
    web_fetch
)

class TestCheckVehicleSafety:
    """Tests para la función check_vehicle_safety con mock de httpx"""
    
    @pytest.mark.asyncio
    async def test_successful_vehicle_lookup(self):
        """Test successful NHTSA API response"""
        
        # Mock NHTSA API responses
        mock_response_recalls = Mock()
        mock_response_recalls.json.return_value = {
            "Count": 1,
            "Results": [
                {
                    "CampaignNumber": "20V123456",
                    "Component": "ENGINE",
                    "Summary": "Engine may stall unexpectedly",
                    "Consequence": "Vehicle stall increases risk of crash",
                    "Remedy": "Dealers will replace engine control module",
                    "Date": "2020-03-15"
                }
            ]
        }
        mock_response_recalls.status_code = 200
        
        mock_response_ratings = Mock()
        mock_response_ratings.json.return_value = {
            "Count": 1,
            "Results": [
                {
                    "OverallRating": "5",
                    "FrontalCrashRating": "4", 
                    "SideCrashRating": "5",
                    "RolloverRating": "4"
                }
            ]
        }
        mock_response_ratings.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            # Configure mock client
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock both API calls
            mock_client_instance.get.side_effect = [
                mock_response_recalls,  # First call for recalls
                mock_response_ratings   # Second call for ratings
            ]
            
            # Test the function
            result = await check_vehicle_safety(
                make="BMW", 
                model="Series 3", 
                year=2020
            )
            
            # Assertions
            assert result["success"] is True
            assert result["data"]["make"] == "BMW"
            assert result["data"]["model"] == "Series 3"
            assert result["data"]["year"] == 2020
            assert len(result["data"]["recalls"]) == 1
            assert result["data"]["recalls"][0]["campaign_number"] == "20V123456"
            assert result["data"]["safety_ratings"]["overall_rating"] == "5"
            
            # Verify API calls were made
            assert mock_client_instance.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_recalls_found(self):
        """Test when no recalls are found"""
        
        mock_response = Mock()
        mock_response.json.return_value = {"Count": 0, "Results": []}
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response
            
            result = await check_vehicle_safety(make="Toyota", model="Corolla")
            
            assert result["success"] is True
            assert len(result["data"]["recalls"]) == 0
            assert "No recalls found" in str(result["recommendations"])
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.side_effect = Exception("API Timeout")
            
            result = await check_vehicle_safety(make="Ford", model="Focus")
            
            assert result["success"] is False
            assert "API Timeout" in result["error"]
    
    @pytest.mark.asyncio 
    async def test_with_vin_parameter(self):
        """Test with VIN parameter"""
        
        mock_response = Mock()
        mock_response.json.return_value = {"Count": 0, "Results": []}
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response
            
            result = await check_vehicle_safety(
                make="Honda", 
                model="Civic", 
                vin="1HGCM82633A004352"
            )
            
            assert result["success"] is True
            assert result["data"]["vin"] == "1HGCM82633A004352"


class TestLLMExtractVehicleInfo:
    """Tests para llm_extract_vehicle_info con mock de LLM providers"""
    
    @pytest.mark.asyncio
    async def test_successful_gemini_extraction(self):
        """Test successful extraction using Gemini"""
        
        mock_response = Mock()
        mock_response.text = '{"make": "BMW", "model": "X5", "year": 2021, "vin": ""}'
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model_instance = Mock()
            mock_model.return_value = mock_model_instance
            mock_model_instance.generate_content.return_value = mock_response
            
            result = await llm_extract_vehicle_info("I want to check BMW X5 2021 safety")
            
            assert result["success"] is True
            assert result["data"]["make"] == "BMW"
            assert result["data"]["model"] == "X5"
            assert result["data"]["year"] == 2021
    
    @pytest.mark.asyncio
    async def test_openai_fallback(self):
        """Test fallback to OpenAI when Gemini fails"""
        
        # Mock OpenAI response
        mock_openai_response = Mock()
        mock_openai_response.choices = [
            Mock(message=Mock(content='{"make": "Toyota", "model": "Camry", "year": 2020, "vin": ""}'))
        ]
        
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            # Gemini fails
            mock_gemini.side_effect = Exception("Gemini API Error")
            
            with patch('openai.ChatCompletion.create') as mock_openai:
                mock_openai.return_value = mock_openai_response
                
                result = await llm_extract_vehicle_info("Toyota Camry 2020 recall check")
                
                assert result["success"] is True
                assert result["data"]["make"] == "Toyota"
                assert result["data"]["model"] == "Camry"
    
    @pytest.mark.asyncio
    async def test_regex_fallback(self):
        """Test regex fallback when both LLMs fail"""
        
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            mock_gemini.side_effect = Exception("No API key")
            
            with patch('openai.ChatCompletion.create') as mock_openai:
                mock_openai.side_effect = Exception("No API key")
                
                result = await llm_extract_vehicle_info("Ford F-150 2019 safety information")
                
                # Should use regex extraction
                assert result["success"] is True
                assert result["data"]["make"] == "Ford"
                assert result["data"]["model"] == "F-150"
                assert result["data"]["year"] == 2019
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON from LLM"""
        
        mock_response = Mock()
        mock_response.text = "This is not valid JSON"
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model_instance = Mock()
            mock_model.return_value = mock_model_instance
            mock_model_instance.generate_content.return_value = mock_response
            
            result = await llm_extract_vehicle_info("BMW Series 3")
            
            # Should fall back to regex
            assert result["success"] is True
            assert result["data"]["make"] == "BMW"
            assert result["data"]["model"] == "Series"


class TestSendEmailSMTP:
    """Tests para send_email_smtp con servidor SMTP simulado"""
    
    @pytest.mark.asyncio
    async def test_successful_email_send(self):
        """Test successful email sending"""
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await send_email_smtp(
                to_email="test@example.com",
                subject="Test Report",
                body="Test email body",
                attachment_path=None
            )
            
            assert result["success"] is True
            assert "test@example.com" in result["message"]
            
            # Verify SMTP methods were called
            mock_server.starttls.assert_called_once()
            mock_server.sendmail.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_with_attachment(self):
        """Test email with attachment"""
        
        # Create temporary file for attachment
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test attachment content")
            temp_file = f.name
        
        try:
            with patch('smtplib.SMTP') as mock_smtp:
                mock_server = Mock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email_smtp(
                    to_email="test@example.com",
                    subject="Report with attachment",
                    body="Email with attachment",
                    attachment_path=temp_file
                )
                
                assert result["success"] is True
                assert "attachment" in result["message"].lower()
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_smtp_connection_error(self):
        """Test SMTP connection failure"""
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = ConnectionError("SMTP server unavailable")
            
            result = await send_email_smtp(
                to_email="test@example.com",
                subject="Test",
                body="Test"
            )
            
            assert result["success"] is False
            assert "SMTP server unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_simulation_mode(self):
        """Test simulation mode when SMTP_HOST is localhost"""
        
        with patch.dict(os.environ, {'SMTP_HOST': 'localhost', 'SMTP_PORT': '1025'}):
            result = await send_email_smtp(
                to_email="test@example.com",
                subject="Simulated email",
                body="This is simulated"
            )
            
            # In simulation mode, should always succeed
            assert result["success"] is True
            assert "simulated" in result["message"].lower()


class TestGenerateMarkdownReport:
    """Tests para generate_markdown_report"""
    
    @pytest.mark.asyncio
    async def test_successful_report_generation(self):
        """Test successful report generation"""
        
        result = await generate_markdown_report(
            title="Test Vehicle Report",
            content="# Vehicle Safety Analysis\n\nThis is test content."
        )
        
        assert result["success"] is True
        assert result["path"].endswith('.md')
        
        # Verify file was created
        assert os.path.exists(result["path"])
        
        # Verify content
        with open(result["path"], 'r') as f:
            content = f.read()
            assert "Test Vehicle Report" in content
            assert "Vehicle Safety Analysis" in content
        
        # Cleanup
        os.unlink(result["path"])
    
    @pytest.mark.asyncio
    async def test_report_with_metadata(self):
        """Test report generation with metadata"""
        
        result = await generate_markdown_report(
            title="BMW X5 Safety Report",
            content="Safety analysis content",
            metadata={"make": "BMW", "model": "X5", "year": 2021}
        )
        
        assert result["success"] is True
        
        # Check metadata is included
        with open(result["path"], 'r') as f:
            content = f.read()
            assert "BMW" in content
            assert "X5" in content
            assert "2021" in content
        
        os.unlink(result["path"])


class TestWebFetch:
    """Tests para web_fetch con mock de httpx"""
    
    @pytest.mark.asyncio
    async def test_successful_web_fetch(self):
        """Test successful web content fetching"""
        
        mock_response = Mock()
        mock_response.text = "<html><body><h1>Test Page</h1><p>Content here</p></body></html>"
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response
            
            result = await web_fetch("https://example.com")
            
            assert result["success"] is True
            assert "Test Page" in result["data"]["content"]
            assert result["data"]["url"] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_web_fetch_error(self):
        """Test web fetch error handling"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.side_effect = Exception("Network error")
            
            result = await web_fetch("https://invalid-url.com")
            
            assert result["success"] is False
            assert "Network error" in result["error"]


# Pytest configuration and fixtures
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for tests"""
    output_dir = tmp_path / "test_outputs"
    output_dir.mkdir()
    return output_dir

# Integration test
class TestMCPToolsIntegration:
    """Integration tests for MCP tools workflow"""
    
    @pytest.mark.asyncio
    async def test_full_vehicle_analysis_workflow(self):
        """Test complete workflow from text extraction to report generation"""
        
        # Mock all external services
        with patch('google.generativeai.GenerativeModel') as mock_gemini, \
             patch('httpx.AsyncClient') as mock_http, \
             patch('smtplib.SMTP') as mock_smtp:
            
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini.return_value = mock_gemini_instance
            mock_gemini_instance.generate_content.return_value.text = (
                '{"make": "Tesla", "model": "Model 3", "year": 2022, "vin": ""}'
            )
            
            mock_http_instance = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_http_instance
            
            mock_safety_response = Mock()
            mock_safety_response.json.return_value = {"Count": 0, "Results": []}
            mock_safety_response.status_code = 200
            mock_http_instance.get.return_value = mock_safety_response
            
            mock_smtp_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_server
            
            # Run workflow
            # 1. Extract vehicle info
            extract_result = await llm_extract_vehicle_info(
                "Please check Tesla Model 3 2022 safety"
            )
            
            assert extract_result["success"] is True
            vehicle_data = extract_result["data"]
            
            # 2. Check safety
            safety_result = await check_vehicle_safety(
                make=vehicle_data["make"],
                model=vehicle_data["model"],
                year=vehicle_data["year"]
            )
            
            assert safety_result["success"] is True
            
            # 3. Generate report
            report_result = await generate_markdown_report(
                title=f"Safety Report - {vehicle_data['make']} {vehicle_data['model']}",
                content="# Vehicle Safety Analysis\n\nNo recalls found."
            )
            
            assert report_result["success"] is True
            
            # 4. Send notification email
            email_result = await send_email_smtp(
                to_email="owner@example.com",
                subject="Vehicle Safety Report Ready",
                body="Your report has been generated",
                attachment_path=report_result["path"]
            )
            
            assert email_result["success"] is True
            
            # Cleanup
            if os.path.exists(report_result["path"]):
                os.unlink(report_result["path"])

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])