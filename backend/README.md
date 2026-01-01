# DocLens Backend

Python FastAPI backend for the DocLens document analyzer application.

## Features

- 📄 **Document Upload**: Support for PDF, DOCX, TXT, and image files
- 🤖 **AI Analysis**: Powered by LangChain with OpenAI
- 🔍 **Five Analysis Actions**:
  - **Summarize**: Generate document summaries with key findings
  - **Extract Structured**: Extract entities, dates, amounts, etc.
  - **Classify**: Categorize documents by type
  - **QA**: Answer questions about document content
  - **Transform**: Convert documents to different formats

## Tech Stack

- **FastAPI** 0.128.0 - Modern async web framework
- **LangChain** 1.2.0 - LLM application framework
- **LangChain-OpenAI** 1.1.6 - OpenAI integration
- **PyMuPDF** 1.26.7 - PDF extraction
- **python-docx** 1.2.0 - DOCX extraction
- **Pydantic** 2.11.4 - Data validation

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access API Docs

Open http://localhost:8000/docs for interactive API documentation.

## API Endpoints

### POST /api/upload

Upload a document for analysis.

**Request**: `multipart/form-data` with `file` field

**Response**:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "file": {
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size_bytes": 12345,
    "file_type": "pdf",
    "page_count": 10
  },
  "limits": { ... },
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

### POST /api/run

Run an analysis action on an uploaded document.

**Request**:
```json
{
  "job_id": "uuid",
  "action": "summarize",
  "options": {},
  "refine": "Keep it brief"
}
```

**Actions**:
- `summarize` - Generate summary
- `extract_structured` - Extract entities and data
- `classify` - Classify document type
- `qa` - Answer questions (requires `question` in options)
- `transform` - Transform document format

### GET /api/job/{job_id}

Get job status and results.

**Response**:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "action": "summarize",
  "result": {
    "title": "Document Title",
    "summary": "...",
    "bullets": [...],
    "key_findings": [...],
    "risks": [...]
  },
  "metrics": { ... }
}
```

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for text analysis |
| `OPENAI_VISION_MODEL` | `gpt-4o-mini` | Model for vision tasks |
| `MAX_PDF_PAGES` | `50` | Maximum PDF pages |
| `RATE_LIMIT_UPLOADS_PER_HOUR` | `5` | Upload rate limit |
| `RATE_LIMIT_RUNS_PER_HOUR` | `20` | Run rate limit |
| `STORAGE_TTL_MINUTES` | `60` | Job expiration time |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app and routes
│   ├── config.py            # Configuration settings
│   ├── models/              # Pydantic models
│   │   ├── api_models.py    # API request/response
│   │   └── ir_models.py     # Document IR
│   ├── ingest/              # File handling
│   │   ├── validate.py      # Validation
│   │   ├── storage.py       # File storage
│   │   └── mime.py          # MIME detection
│   ├── extract/             # Document extraction
│   │   ├── pdf_extract.py   # PDF extraction
│   │   ├── docx_extract.py  # DOCX extraction
│   │   ├── image_extract.py # Image handling
│   │   └── text_extract.py  # Text file extraction
│   ├── vision/              # Vision processing
│   │   ├── gate.py          # Vision gating
│   │   └── langchain_vision.py  # LangChain vision
│   ├── actions/             # Analysis actions
│   │   ├── router.py        # Action dispatch
│   │   ├── summarize.py     # Summarize
│   │   ├── extract_structured.py
│   │   ├── classify.py
│   │   ├── qa.py
│   │   └── transform.py
│   ├── jobs/                # Job management
│   │   ├── store.py         # In-memory store
│   │   └── cleanup.py       # TTL cleanup
│   └── utils/               # Utilities
│       ├── rate_limit.py    # Rate limiting
│       ├── timeouts.py      # Timeouts
│       └── hashing.py       # File hashing
├── tests/                   # Unit tests
├── requirements.txt
└── .env.example
```

## Running Tests

```bash
pytest tests/ -v
```

## Rate Limits

- **Uploads**: 5 per hour per IP
- **Runs**: 20 per hour per IP

## File Limits

- **PDF**: 20MB max, 50 pages max
- **DOCX**: 10MB max, 500k characters max
- **TXT**: 5MB max
- **Images**: 10MB max

## Notes

- This is a **Proof of Concept** with in-memory job storage
- Jobs expire after 60 minutes (configurable)
- Background cleanup runs every 5 minutes
