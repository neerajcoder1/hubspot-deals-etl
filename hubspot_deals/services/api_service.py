import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, Retrying
from loki_logger import get_logger, log_api_call

class RateLimitException(Exception):
    pass

class TransientAPIException(Exception):
    pass

class AuthException(Exception):
    pass

class APIService:
    """
    Service for interacting with HubSpot CRM API v3
    """
    def __init__(self, base_url: str = "https://api.hubapi.com", test_delay_seconds: float = 0):
        self.base_url = base_url.rstrip('/')
        self.test_delay_seconds = test_delay_seconds
        self.logger = get_logger(__name__)
        self.session = requests.Session()
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'HubSpot-Deals-Data-Extraction-Service/1.0'
        })
        
        # Rate Limiting state (150 requests / 10 seconds)
        self.request_timestamps = []
        
    def _rate_limit(self):
        """Enforce 150 requests per 10 seconds"""
        now = time.time()
        # Remove timestamps older than 10 seconds
        self.request_timestamps = [t for t in self.request_timestamps if now - t < 10.0]
        
        if len(self.request_timestamps) >= 150:
            sleep_time = 10.0 - (now - self.request_timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
            # Re-evaluate
            self._rate_limit()
        else:
            self.request_timestamps.append(time.time())

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        self._rate_limit()
        start_time = datetime.utcnow()
        try:
            response = self.session.request(method, url, **kwargs)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if response.status_code == 401:
                raise AuthException("Authentication failed (401)")
            elif response.status_code == 429:
                raise RateLimitException("Rate limited (429)")
            elif response.status_code >= 500:
                raise TransientAPIException(f"Transient server error: {response.status_code}")
                
            response.raise_for_status()
            
            log_api_call(
                self.logger,
                "hubspot_deals_api_call",
                method=method,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            return response
            
        except requests.exceptions.RequestException as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            log_api_call(
                self.logger,
                "hubspot_deals_api_call",
                method=method,
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                duration_ms=round(duration_ms, 2)
            )
            raise

    def get_data(self, access_token: str, limit: int = 100, after: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get deals from HubSpot API v3 with retries and exponential backoff
        """
        if self.test_delay_seconds > 0:
            time.sleep(self.test_delay_seconds)
            
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': min(limit, 100)}
        
        # Request specific properties as per assignment
        params['properties'] = "dealname,amount,dealstage,closedate"
        
        if after:
            params['after'] = after
            
        url = f"{self.base_url}/crm/v3/objects/deals"
        
        # Exponential backoff for RateLimit and Transient errors. DO NOT retry auth errors.
        for attempt in Retrying(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((RateLimitException, TransientAPIException)),
            reraise=True
        ):
            with attempt:
                response = self._make_request('GET', url, params=params, headers=headers)
                return response.json()