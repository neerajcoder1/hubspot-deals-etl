from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from contextlib import asynccontextmanager

from config import get_config
from api.routers import api_router
from models.database import initialize_database

config = get_config(os.getenv("ENV", "default"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    initialize_database()
    yield
    # Clean up resources if needed

description = """
**HubSpot Deals ETL Microservice** 🚀

A production-ready data extraction microservice that securely fetches Deal records from the **HubSpot CRM API v3** and loads them into a **PostgreSQL** database using the **DLT (Data Load Tool)** framework.

### Features
* **Multi-Tenant Isolation**: Data is strictly segregated per organization schema.
* **Robust Rate Limiting**: Internal rolling-window rate limiter respects HubSpot's 150 req/10s limit.
* **Fault Tolerance**: Automatic exponential backoff and retries via Tenacity.
* **Background Jobs**: Non-blocking asynchronous extraction pipeline.
"""

tags_metadata = [
    {
        "name": "Scans",
        "description": "Operations for triggering, monitoring, and retrieving HubSpot Deal extractions.",
    }
]

app = FastAPI(
    title="HubSpot Deals ETL API",
    description=description,
    version=config.APP_VERSION,
    contact={
        "name": "Data Engineering Team",
        "url": "https://github.com/neerajcoder1/hubspot-deals-etl",
    },
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1, # Hide schemas at the bottom
        "displayRequestDuration": True,
        "syntaxHighlight.theme": "monokai"
    }
)
# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def index():
    return {
        "service": config.APP_TITLE,
        "version": config.APP_VERSION,
        "documentation": "/docs",
        "health": "/health",
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5200))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    uvicorn.run("app:app", host=host, port=port, reload=debug)
