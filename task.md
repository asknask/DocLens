# DocLens - Document Analyzer PoC

## Phase 1: Planning & Setup
- [x] Create implementation plan
- [x] Get user approval on plan

## Phase 2: Backend Implementation
- [x] Project scaffold and configuration
  - [x] Create directory structure
  - [x] requirements.txt and config.py
  - [x] Environment setup
- [x] Core models
  - [x] API models (Pydantic v2)
  - [x] Document IR models
- [x] Ingest layer
  - [x] File validation and limits
  - [x] MIME detection
  - [x] Storage with TTL cleanup
- [x] Extraction layer
  - [x] PDF extraction (PyMuPDF)
  - [x] DOCX extraction (python-docx)
  - [x] Image extraction
  - [ ] Textract fallback (optional - AWS)
- [x] Vision layer
  - [x] Vision gating logic
  - [x] OpenAI vision integration (via LangChain)
- [x] Actions layer (using LangChain)
  - [x] Instruction normalizer
  - [x] Summarize action
  - [x] Extract structured action
  - [x] Classify action
  - [x] QA action
  - [x] Transform action
- [x] Jobs layer
  - [x] Job store (in-memory)
  - [x] TTL cleanup background task
- [x] Utilities
  - [x] Rate limiting
  - [x] Timeouts
  - [x] Hashing
- [x] API endpoints
  - [x] POST /api/upload
  - [x] POST /api/run
  - [x] GET /api/job/{job_id}

## Phase 3: Frontend Implementation
- [x] Next.js project setup
- [x] Components
  - [x] UploadBox
  - [x] ActionForm
  - [x] JsonViewer
  - [x] LimitsNotice
- [x] Main page flow
- [x] API integration

## Phase 4: Integration & Docker
- [x] docker-compose.yml
- [x] .env.example
- [x] Root README.md
- [x] Backend README.md
- [x] Frontend README.md

## Phase 5: Testing & Verification
- [x] Unit tests for instruction normalizer
- [x] Unit tests for limits validation
- [ ] Manual end-to-end testing

