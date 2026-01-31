# DocLens - AI Document Analyzer

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.128-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangChain-1.2-green?style=for-the-badge" alt="LangChain" />
</div>

<br />

A full-stack document analysis application powered by AI. Upload PDFs, DOCX files, or images and get instant analysis with structured JSON output.

## ✨ Features

- 📄 **Multi-format Support**: TXT, PDF, DOCX, JPEG, PNG, WebP, GIF
- 🤖 **AI-Powered Analysis**: Leverages LangChain + OpenAI for intelligent processing
- 🔍 **Five Analysis Actions**:
  - **Summarize**: Generate summaries with key findings
  - **Extract Structured**: Pull entities, dates, amounts, and more
  - **Classify**: Categorize documents by type
  - **Q&A**: Ask questions about document content
  - **Transform**: Convert to different formats
- � **Dual Output Format**: View results as human-readable text or structured JSON
- �👁️ **Vision Processing**: Automatic OCR for scanned documents and images
- ⚡ **Real-time Updates**: Live status during processing
- 🛡️ **Rate Limiting**: Built-in abuse prevention
- 🎨 **Modern UI**: Beautiful dark theme with animations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API

### 1. Clone & Configure

```bash
# From project root
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Setup Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Navigate to http://localhost:3000

## 📁 Project Structure

```
DocLens/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── main.py         # API endpoints
│   │   ├── config.py       # Configuration
│   │   ├── models/         # Pydantic models
│   │   ├── ingest/         # File handling
│   │   ├── extract/        # Document extraction
│   │   ├── vision/         # Vision processing
│   │   ├── actions/        # Analysis actions
│   │   ├── jobs/           # Job management
│   │   └── utils/          # Utilities
│   ├── tests/              # Unit tests
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/            # App router pages
│   │   ├── components/     # React components
│   │   └── lib/            # API client
│   └── package.json
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── docker-compose.yml      # Docker setup
└── README.md
```

## 🔧 Configuration

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | Model for text analysis |
| `OPENAI_VISION_MODEL` | ❌ | `gpt-4o-mini` | Model for vision tasks |
| `MAX_PDF_PAGES` | ❌ | `50` | Maximum PDF pages |
| `RATE_LIMIT_UPLOADS_PER_HOUR` | ❌ | `5` | Upload rate limit |
| `STORAGE_TTL_MINUTES` | ❌ | `60` | Job expiration time |

See `.env.example` in the project root for all options.

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/upload` | Upload document | Returns job_id |
| `POST /api/run` | Run analysis | Executes action |
| `GET /api/job/{id}` | Get status | Returns result |
| `GET /health` | Health check | Returns status |

### Example: Upload and Analyze

```bash
# Upload a document
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf"

# Run summarization
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"job_id": "xxx", "action": "summarize"}'

# Get result
curl http://localhost:8000/api/job/xxx
```

## 🐳 Docker Setup

```bash
# Start both services
docker-compose up

# Or build fresh
docker-compose up --build
```

## 📊 Limits

| Resource | Limit |
|----------|-------|
| PDF file size | 20 MB |
| PDF pages | 50 |
| DOCX file size | 10 MB |
| DOCX characters | 500,000 |
| Image file size | 10 MB |
| Uploads per hour | 5 |
| Runs per hour | 20 |
| Job TTL | 60 minutes |

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend lint
cd frontend
npm run lint
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.128.0 - Async web framework
- **LangChain** 1.2.0 - LLM application framework
- **LangChain-OpenAI** 1.1.6 - OpenAI integration
- **PyMuPDF** 1.26.7 - PDF processing
- **python-docx** 1.2.0 - DOCX processing
- **Pydantic** 2.11.4 - Data validation

### Frontend
- **Next.js** 15 - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **React** 19 - UI library

## ⚠️ Limitations

This is a **Proof of Concept (PoC)** with the following limitations:

- **In-memory storage**: Jobs are lost on restart
- **No authentication**: Open access (use rate limiting)
- **Single instance**: Not designed for horizontal scaling
- **No persistence**: Results not stored permanently

<div align="center">
  <p>Built with ❤️ using FastAPI, LangChain, and Next.js</p>
</div>
