# Bulk Certificate Generator API

A production-grade, asynchronous backend API built with **FastAPI**, **SQLAlchemy**, and **ReportLab** for bulk certificate generation, real-time progress tracking, and batch zip downloading.

---

## 📌 Architecture & Features

- **Asynchronous Bulk Processing**: Accepts bulk recipient lists, returning `202 Accepted` immediately with background task execution.
- **Granular Fault Tolerance**: Per-item validation and `try/except` execution ensure an invalid email, corrupted name, or rendering failure never stops or blocks the remaining recipients.
- **Precision PDF Generation**: ReportLab engine generating high-resolution landscape certificates of completion with border ornaments, verification seals, and unique certificate identifiers.
- **Real-Time Job Status & Progress**: Tracks item-by-item progress percentages, success/failure counts, and detailed error messages.
- **Single & Bulk Downloads**: Download individual PDFs directly or batch-download all successful certificates for a job as a single ZIP archive.
- **Full Test Coverage**: 16 comprehensive unit, integration, and fault-tolerance tests using `pytest` and `TestClient`.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Core programming language with strict type hints |
| **FastAPI** | High-performance asynchronous web framework |
| **SQLAlchemy 2.0** | Relational ORM for schema definitions and queries |
| **SQLite** | Lightweight, zero-config relational database |
| **ReportLab** | Vector PDF certificate drawing and rendering |
| **Pydantic v2** | Request/response data validation and serialization |
| **pytest + httpx** | Automated test suite and HTTP client testing |

---

## 📂 Project Structure

```text
certificate-generator-api/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entrypoint, CORS, lifespan, routes
│   ├── config.py                        # Centralized settings and environment variables
│   ├── database.py                      # SQLAlchemy engine, session maker, get_db dependency
│   ├── models.py                        # Database models (Job, Certificate) & Enums
│   ├── schemas.py                       # Pydantic validation & response schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── jobs.py                      # /api/jobs endpoints (create, status, list, zip)
│   │   └── certificates.py              # /api/certificates/{id}/download endpoint
│   └── services/
│       ├── __init__.py
│       ├── certificate_generator.py     # ReportLab PDF template rendering
│       └── job_processor.py             # Background task, validation, per-item execution
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Test engine, isolation fixtures, and client
│   ├── test_jobs.py                     # Job creation, validation, status & progress tests
│   ├── test_certificates.py             # PDF validity, single download, and ZIP tests
│   ├── test_fault_tolerance.py          # Per-item error isolation & mock crash tests
│   └── test_services.py                 # Direct unit tests for PDF generator & validator
├── generated_certificates/              # Directory where generated PDF certificates reside
│   └── .gitkeep
├── requirements.txt                     # Pinned project dependencies
├── .gitignore                           # Git ignore rules
└── README.md                            # Complete setup, API documentation, and decisions
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Clone Repository & Create Virtual Environment
```bash
git clone <your-repo-url>
cd certificate-generator-api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (CMD):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the API Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The server will start at `http://127.0.0.1:8000`.

Interactive API Documentation:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the complete test suite with verbose output:
```bash
pytest -v
```

Run tests with short summary:
```bash
pytest -q
```

All 16 tests cover:
- Bulk job submission returning 202 Accepted.
- Empty recipient list rejection (422).
- Exceeded recipient limits rejection (422).
- Non-blocking error handling for bad emails and missing names.
- PDF generation validation (non-empty, `%PDF` magic bytes).
- Live progress metrics and completion states.
- Mocked generator crash ensuring other recipients still succeed (`COMPLETED_WITH_ERRORS`).
- Individual PDF downloads and bulk ZIP downloads.

---

## 📡 API Endpoints & Example Requests

### 1. Create a Bulk Generation Job
`POST /api/jobs`  
**Status**: `202 Accepted`

```bash
curl -X POST "http://127.0.0.1:8000/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": [
      {
        "name": "Alan Turing",
        "email": "alan.turing@example.com",
        "course": "Theoretical Computer Science",
        "date": "2026-10-09",
        "extra_fields": {"grade": "A+", "honors": "Distinction"}
      },
      {
        "name": "Ada Lovelace",
        "email": "ada.lovelace@example.com",
        "course": "Analytical Engine Programming",
        "date": "2026-10-09"
      },
      {
        "name": "Invalid Recipient",
        "email": "bad-email-address",
        "course": "Analytical Engine Programming",
        "date": "2026-10-09"
      }
    ]
  }'
```

**Response (202 Accepted)**:
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "PENDING",
  "total_recipients": 3,
  "created_at": "2026-10-09T05:00:00Z",
  "message": "Job accepted and queued for background processing."
}
```

---

### 2. Check Job Status & Progress
`GET /api/jobs/{job_id}`  
**Status**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/api/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
```

**Response (200 OK)**:
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "COMPLETED_WITH_ERRORS",
  "total": 3,
  "success_count": 2,
  "failed_count": 1,
  "progress_percentage": 100.0,
  "error_message": null,
  "created_at": "2026-10-09T05:00:00Z",
  "updated_at": "2026-10-09T05:00:02Z"
}
```

---

### 3. List All Certificates for a Job
`GET /api/jobs/{job_id}/certificates`  
**Status**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/api/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/certificates"
```

**Response (200 OK)**:
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "total": 3,
  "certificates": [
    {
      "certificate_id": "b11a91d2-06e0-47ec-a4fc-b8f2d5930058",
      "recipient_name": "Alan Turing",
      "recipient_email": "alan.turing@example.com",
      "course_name": "Theoretical Computer Science",
      "issue_date": "2026-10-09",
      "status": "SUCCESS",
      "error_message": null,
      "download_url": "/api/certificates/b11a91d2-06e0-47ec-a4fc-b8f2d5930058/download",
      "created_at": "2026-10-09T05:00:00Z"
    },
    {
      "certificate_id": "f898ad95-0fcb-488b-b8c1-140c83a73df1",
      "recipient_name": "Invalid Recipient",
      "recipient_email": "bad-email-address",
      "course_name": "Analytical Engine Programming",
      "issue_date": "2026-10-09",
      "status": "FAILED",
      "error_message": "Invalid email address format: 'bad-email-address'. The email address is not valid. It must have exactly one @-sign.",
      "download_url": null,
      "created_at": "2026-10-09T05:00:00Z"
    }
  ]
}
```

---

### 4. Download an Individual PDF Certificate
`GET /api/certificates/{certificate_id}/download`  
**Status**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/api/certificates/b11a91d2-06e0-47ec-a4fc-b8f2d5930058/download" \
  --output certificate_alan_turing.pdf
```

---

### 5. Download All Successful Certificates as a ZIP Archive
`GET /api/jobs/{job_id}/download`  
**Status**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/api/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/download" \
  --output all_certificates.zip
```

---

## 🏛️ Architectural & Design Decisions

### 1. Asynchronous Processing: FastAPI `BackgroundTasks` vs. Celery
- **Why `BackgroundTasks` for this assignment**:
  - **Zero external infrastructure**: Celery requires a dedicated message broker (Redis or RabbitMQ) and separate worker processes. `BackgroundTasks` runs in-process using Starlette's asyncio thread pool, keeping deployment, local execution, and automated testing completely frictionless.
  - **Immediate Client Response**: Returns HTTP `202 Accepted` instantly so the client is not blocked by CPU-intensive PDF canvas rendering.
- **Production Trade-offs**:
  - *Limitation*: In-process background tasks share CPU and memory with the web server. If the server restarts or crashes mid-job, pending tasks in memory can be lost.
  - *Production Upgrade*: In a production multi-replica environment, we would swap `BackgroundTasks` with **Celery + Redis** or **ARQ / Celery with RabbitMQ** to support distributed workers, dedicated queues, automatic retries, and persistence across server restarts.

### 2. Per-Item Fault Isolation
- A bulk job might have hundreds of recipients. One misspelled email or unrenderable character should never invalidate the other 499 certificates.
- Each recipient is processed inside its own isolated `try...except` block:
  - If valid: PDF is generated and status is marked `SUCCESS`.
  - If invalid: status is marked `FAILED` with an explicit, human-readable `error_message`.
- Status resolution:
  - All succeeded $\rightarrow$ `COMPLETED`
  - Succeeded + Failed mixed $\rightarrow$ `COMPLETED_WITH_ERRORS`
  - All failed $\rightarrow$ `FAILED`

### 3. Database Schema & Concurrency
- `Job` table tracks macro execution metrics (`total_recipients`, `success_count`, `failed_count`, `status`, `progress_percentage`).
- `Certificate` table holds individual recipient rows, foreign-keyed to `Job.id` with cascade deletion.
- Background jobs open an isolated SQLAlchemy session (`SessionLocal()`), committing progress incrementally per item. This guarantees that `GET /api/jobs/{id}` reflects live, real-time progress while generation is underway.

### 4. File Storage Strategy
- Certificates are saved to a dedicated local directory (`generated_certificates/{certificate_id}.pdf`).
- Database rows only record the canonical `file_path`, separating metadata from binary storage.
- Download endpoints verify that the file actually exists on disk before attempting to stream it.

---

## 🔮 Learnings & Future Scope

1. **Distributed Task Queue (Celery + Redis)**:
   - Decouple rendering CPU load from the API gateway using distributed worker nodes.
2. **Cloud Object Storage (Amazon S3 / Google Cloud Storage)**:
   - Replace local file storage with S3 bucket uploads and provide short-lived pre-signed URLs for downloads.
3. **Automatic Retries & Exponential Backoff**:
   - For transient I/O or rendering failures, implement retry policies before marking a certificate `FAILED`.
4. **Authentication & Multi-Tenancy**:
   - Add OAuth2 / JWT authentication, role-based access control (RBAC), and API keys to isolate jobs by organization.
5. **Dynamic Certificate Templates**:
   - Support custom background images, company logos, custom fonts, and user-supplied Jinja2 / HTML-to-PDF templates.

---

## 📄 License
MIT License. Free for educational and commercial use.
