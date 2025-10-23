# Simple RAG configuration for local integrations
# Set RAG_HTTP_ENDPOINT to the teammate-provided HTTP endpoint for RAG (POST /rag)
# Or set RAG_PYTHON_CLIENT to the import path of a Python module that exposes `query(text)`.

RAG_HTTP_ENDPOINT = "http://localhost:8000/rag"
RAG_PYTHON_CLIENT = "rag_client"

# Timeout for HTTP RAG calls (seconds)
RAG_HTTP_TIMEOUT = 6.0
