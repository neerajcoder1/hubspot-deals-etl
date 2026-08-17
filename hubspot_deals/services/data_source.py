import dlt
import logging
from typing import Dict, Any, Iterator, Optional, Callable
from datetime import datetime, timezone
from loki_logger import get_logger
from .api_service import APIService

def create_data_source(
    job_config: Dict[str, Any],
    auth_config: Dict[str, Any],
    filters: Dict[str, Any],
    checkpoint_callback: Optional[Callable] = None,
    check_cancel_callback: Optional[Callable] = None,
    check_pause_callback: Optional[Callable] = None,
    resume_from: Optional[Dict[str, Any]] = None,
):
    """
    Create DLT source function for HubSpot Deals extraction with checkpointing.
    """
    logger = get_logger(__name__)
    api_service = APIService()

    access_token = auth_config.get("accessToken")
    if not access_token:
        raise ValueError("No access token found in auth configuration")

    tenant_id = job_config.get("organizationId")
    if not tenant_id:
        raise ValueError("No organization ID found (maps to tenant_id)")

    scan_id = job_config.get("scanId", "unknown")

    @dlt.resource(name="hubspot_deals", write_disposition="replace", primary_key="id")
    def get_deals() -> Iterator[Dict[str, Any]]:
        # Initialize state
        after = resume_from.get("cursor") if resume_from else None
        page_count = resume_from.get("page_number", 0) if resume_from else 0
        total_records = resume_from.get("records_processed", 0) if resume_from else 0

        checkpoint_interval = 5

        while True:
            # Check for cancellation
            if check_cancel_callback and check_cancel_callback(scan_id):
                logger.info(f"Scan {scan_id} cancelled.")
                break

            try:
                data = api_service.get_data(access_token, limit=100, after=after)
                results = data.get("results", [])
                
                for record in results:
                    props = record.get("properties", {})
                    yield {
                        "id": record.get("id"),
                        "dealname": props.get("dealname"),
                        "amount": props.get("amount"),
                        "dealstage": props.get("dealstage"),
                        "closedate": props.get("closedate"),
                        "_extracted_at": datetime.now(timezone.utc).isoformat(),
                        "_scan_id": scan_id,
                        "_tenant_id": tenant_id
                    }
                
                page_records = len(results)
                total_records += page_records
                page_count += 1
                
                paging = data.get("paging", {})
                next_cursor = paging.get("next", {}).get("after")
                
                if checkpoint_callback and (page_count % checkpoint_interval == 0 or not next_cursor):
                    checkpoint_callback(scan_id, {
                        "phase": "hubspot_deals",
                        "records_processed": total_records,
                        "cursor": next_cursor,
                        "page_number": page_count,
                        "batch_size": 100
                    })

                if not next_cursor:
                    break
                
                after = next_cursor

            except Exception as e:
                logger.error(f"Failed to fetch data page: {e}")
                raise

    return [get_deals]