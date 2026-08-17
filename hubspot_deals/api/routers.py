from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid
import logging
from datetime import datetime

from config import get_config
from services.extraction_service import ExtractionService
from models.models import JobStatus

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")
scan_router = APIRouter(prefix="/scan", tags=["Scan"])

config = get_config()
extraction_service = ExtractionService(config.get_extraction_config(), source_type="hubspot_deals")

class AuthConfig(BaseModel):
    accessToken: str = Field(..., description="HubSpot access token")

class ScanRequest(BaseModel):
    organizationId: str = Field(..., description="Tenant / Organization ID")
    type: Optional[List[str]] = Field(default=["deals"], description="Type of extraction")
    auth: AuthConfig = Field(..., description="Authentication configuration")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Filters for extraction")

@scan_router.post("/start")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous extraction job."""
    job_id = str(uuid.uuid4())
    
    request_config = {
        "scanId": job_id,
        "organizationId": request.organizationId,
        "type": request.type,
        "auth": request.auth.model_dump(),
        "filters": request.filters
    }
    
    # Pass the request_config to extraction_service.start_scan
    # extraction_service.start_scan already spawns a background task via asyncio.create_task internally.
    # However, to conform with FastAPI, we could use background_tasks, but ExtractionService already handles it.
    # We will await it to ensure initialization completes and returns status.
    try:
        result = await extraction_service.start_scan(request_config)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to start scan"))
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "Scan initialization accepted and is now processing in the background."
        }
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@scan_router.get("/status/{job_id}")
async def get_scan_status(job_id: str):
    """Get the status of a specific scan"""
    status_data = extraction_service.get_scan_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail=f"No scan found with ID: {job_id}")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": status_data.get("status"),
        "created_at": status_data.get("startTime"),
        "completed_at": status_data.get("endTime"),
        "records_extracted": status_data.get("recordsExtracted"),
        "error_message": status_data.get("errorMessage")
    }

@scan_router.get("/result/{job_id}")
async def get_scan_result(
    job_id: str, 
    limit: int = Query(50, ge=1, le=1000), 
    offset: int = Query(0, ge=0)
):
    """Get scan results with pagination"""
    result = extraction_service.get_scan_results(job_id, table_name="hubspot_deals", limit=limit, offset=offset)
    
    if not result.get("success"):
        status_code = 404 if "not found" in result.get("message", "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result.get("message"))
        
    return {
        "success": True,
        "data": result.get("data")
    }

@scan_router.post("/cancel/{job_id}")
async def cancel_scan(job_id: str):
    """Cancel a running scan"""
    result = extraction_service.cancel_scan(job_id)
    if not result.get("success"):
        status_code = 404 if "not found" in result.get("message", "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result.get("message"))
    
    return result

@scan_router.delete("/remove/{job_id}")
async def remove_scan(job_id: str):
    """Remove a scan and its data"""
    result = extraction_service.remove_scan(job_id)
    if not result.get("success"):
        status_code = 404 if "not found" in result.get("message", "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result.get("message"))
    
    return result


api_router.include_router(scan_router)
