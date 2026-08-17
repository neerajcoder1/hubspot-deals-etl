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

app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
