# HubSpot Deals ETL Microservice

A production-ready data extraction microservice that securely fetches Deal records from the **HubSpot CRM API v3** and loads them into a **PostgreSQL** database using the **DLT (Data Load Tool)** framework. 

This project was built following strict multi-tenant isolation principles, robust rate-limiting, and modern asynchronous API design.

## 🚀 Technologies Used
- **Language**: Python 3.10+
- **Framework**: FastAPI & Uvicorn
- **Data Pipeline**: DLT (Data Load Tool)
- **Database**: PostgreSQL 15
- **Resilience**: Tenacity (Exponential Backoff)
- **Infrastructure**: Docker & Docker Compose
- **Testing**: Pytest

---

## 🏗 Architecture & Features

### 1. Multi-Tenant Isolation
Data is strictly segregated per organization. When an extraction job is requested, the payload provides an `organizationId`. This ID maps dynamically to an isolated PostgreSQL schema (using DLT).
Every extracted record is enriched with:
- `_tenant_id`: Ensures data belongs to the correct organization boundary.
- `_scan_id`: Tracks the specific extraction job.
- `_extracted_at`: The UTC timestamp of the extraction.

### 2. Robust Rate Limiting
To comply with HubSpot's API limits (150 requests per 10 seconds for Private Apps), the service implements an internal rolling-window rate limiter. Before any API call is made, it verifies the window and dynamically sleeps if the threshold is reached, preventing 429 Too Many Requests errors.

### 3. Fault Tolerance (Tenacity)
Network failures and transient HTTP errors (e.g., 502, 504) are handled seamlessly using the `tenacity` library, which automatically applies exponential backoff and retries the failed requests up to 5 times.

### 4. Background Job Processing
Scans are initiated via a non-blocking API endpoint and run as background tasks. The API provides endpoints to check the status of a job, fetch paginated results, or cancel/remove jobs.

---

## 🛠 How to Run Locally

### Prerequisites
- Docker and Docker Compose installed
- A valid HubSpot Private App Access Token

### Setup
1. Clone the repository and navigate into the folder:
   ```bash
   cd hubspot-deals-etl
   ```
2. Navigate to the core service directory (if not running from root):
   ```bash
   cd hubspot_deals
   ```
3. Set up your environment variables by copying the example file:
   ```bash
   cp .env.example .env
   ```
4. Insert your HubSpot Access token into the `.env` file:
   ```env
   HUBSPOT_ACCESS_TOKEN=your_real_hubspot_token_here
   ```

### Launch
Start the application and PostgreSQL database using Docker Compose:
```bash
docker-compose up --build
```
The FastAPI application will be accessible at: `http://localhost:5200`

---

## 🔌 API Endpoints

Once the application is running, you can access the interactive Swagger UI at:  
👉 **`http://localhost:5200/docs`**

### 1. Start a Scan
**`POST /api/v1/scan/start`**  
Initiates a background extraction job for a specific tenant.
```json
{
  "auth": {
    "accessToken": "string"
  },
  "organizationId": "tenant_123"
}
```

### 2. Check Scan Status
**`GET /api/v1/scan/status/{job_id}`**  
Returns the current state of the job (e.g., `RUNNING`, `COMPLETED`, `FAILED`).

### 3. Fetch Scan Results
**`GET /api/v1/scan/result/{job_id}?limit=100&offset=0`**  
Returns the paginated deal records extracted during the specified job. Strictly enforces tenant isolation at the query level.

### 4. Cancel a Scan
**`POST /api/v1/scan/cancel/{job_id}`**  
Safely halts an actively running background extraction pipeline.

### 5. Remove a Scan
**`DELETE /api/v1/scan/remove/{job_id}`**  
Deletes the job tracking history and entirely drops the isolated PostgreSQL schema associated with that specific scan's data.

---

## 🧪 Testing

Unit tests are written using `pytest`. To run the tests inside a local environment:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```