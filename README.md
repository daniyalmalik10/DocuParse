# DocuParse — Implementation Plan

**Stack:** FastAPI (x3 services) + Celery + Redis + MongoDB + Angular 17+ + Docker Compose + GitHub Actions
**Architecture:** Microservices (Gateway/Auth, Document, Extraction worker) + Angular SPA
**Portfolio goal:** Demonstrate microservices design, async task queues, LLM-powered extraction pipelines — mirroring DoKaSch (MongoDB, async APIs) + DeepAdvisor (LLM integration) work.

---

## What this project is

Upload a resume (PDF or DOCX), the system extracts text, sends it to an LLM for structured parsing, and returns JSON with candidate's name, contact info, skills, work experience, and education. User sees the upload status update in near-real-time (polling) and can view the extracted structured data in a clean UI.

## What this project is NOT

- Not a real ATS (applicant tracking system) — it's a parsing demo
- Not a multi-extraction-type platform — resumes only, schema is fixed (extensibility documented, not implemented)
- Not Kubernetes — Docker Compose is sufficient for portfolio
- Not streaming WebSocket updates — HTTP polling every 2s is simpler and enough for the demo
- Not cloud storage — local filesystem volume is fine, S3 swap documented

## Services

1. **Gateway / Auth service** (FastAPI) — port 8000 — issues JWT, reverse-proxies to other services
2. **Document service** (FastAPI + MongoDB) — port 8001 — upload, metadata CRUD, triggers extraction jobs
3. **Extraction worker** (Celery consumer) — no HTTP port — pulls jobs from Redis, calls LLM, writes results
4. **Angular frontend** — port 4200 dev, static build in prod — talks only to Gateway

**Data stores:**
- MongoDB — document metadata, extraction results
- Redis — Celery broker and result backend
- Local filesystem volume — uploaded files (mounted into Document + Worker services)

**LLM provider:** Groq free tier (fast, OpenAI-compatible). Same provider abstraction pattern as PromptVault but simpler — only one provider needed here.

---

## Phase 0 — Repo & tooling setup

**Goal:** Monorepo layout ready, empty CI wired.

**Tasks:**
- `git init`, create `daniyalmlik/DocuParse` on GitHub
- Monorepo layout:
  ```
  /services
    /gateway
    /document
    /worker
  /frontend
  /shared          Pydantic models shared across services via local package
  /.github/workflows
  docker-compose.yml
  README.md
  ```
- Each Python service has its own `pyproject.toml` and `Dockerfile`
- Root `.gitignore` covers Python + Node + IDE

**Done when:** Repo pushed, empty CI green.

---

## Phase 1 — Shared contracts package

**Goal:** Pydantic models used by multiple services live in one place.

**Tasks:**
- `/shared/docuparse_contracts/` installable as a local editable package
- Define:
  - `UploadMetadata` (filename, content_type, size, user_id, uploaded_at)
  - `ExtractionJob` (job_id, document_id, status, created_at)
  - `JobStatus` enum: `pending`, `processing`, `completed`, `failed`
  - `ResumeExtraction` — the structured output:
    - `full_name: str`
    - `email: Optional[str]`
    - `phone: Optional[str]`
    - `location: Optional[str]`
    - `summary: Optional[str]`
    - `skills: List[str]`
    - `experience: List[WorkExperience]`  (company, title, start, end, bullets)
    - `education: List[Education]`  (institution, degree, year)
  - Error response envelope
- Each service depends on this package via editable install

**Done when:** All three services can import contracts without circular dependencies.

---

## Phase 2 — Gateway / Auth service

**Goal:** FastAPI gateway that issues JWT and forwards requests.

**Tasks:**
- FastAPI app with endpoints:
  - `POST /auth/register` — email + password, stores hashed password in MongoDB (users collection)
  - `POST /auth/login` — returns access + refresh token
  - `POST /auth/refresh`
  - `GET /auth/me`
- JWT using `python-jose` with RS256 — public key shared with other services for verification
- Password hashing with `passlib[bcrypt]`
- Reverse proxy endpoints using `httpx.AsyncClient`:
  - `POST /api/documents/*` → forwards to Document service with validated JWT
  - `GET /api/documents/*` → same
- JWT validation middleware: verifies signature, attaches `user_id` to forwarded request headers
- Tests: auth flow, JWT signing/verification, proxy with auth header forwarding

**Done when:** Can register, log in, call a proxied (but not yet implemented) endpoint and see the gateway forward the request.

---

## Phase 3 — Document service

**Goal:** Upload, store metadata in MongoDB, save file to shared volume, enqueue extraction job.

**Tasks:**
- FastAPI app with endpoints (all require `X-User-Id` header set by gateway):
  - `POST /documents/upload` — multipart file upload, validates type (PDF/DOCX only, max 5MB), saves file to `/data/uploads/<uuid>.<ext>`, inserts metadata, enqueues Celery job, returns `{document_id, job_id, status}`
  - `GET /documents/` — list current user's documents with job status
  - `GET /documents/{id}` — single document with full metadata + extraction result (if completed)
  - `DELETE /documents/{id}` — removes metadata + file
- MongoDB collections: `documents`, `extraction_jobs`
- Index: `documents.user_id + documents.uploaded_at desc` — mirrors DoKaSch "MongoDB query optimization" bullet
- Celery client configured to send tasks to the extraction worker queue
- JWT verification: validates the JWT public key + checks `X-User-Id` header integrity
- Tests: upload flow, user isolation, file size/type validation, job enqueue (mock Celery)

**Done when:** Upload via curl/Postman results in a file on disk, a MongoDB record, and a queued Celery task.

---

## Phase 4 — Extraction worker

**Goal:** Consume jobs, extract text from file, call LLM, save structured result.

**Tasks:**
- Celery worker wired to the same Redis broker
- Task: `extract_resume(document_id: str)`
- Pipeline inside the task:
  1. Load document metadata from MongoDB, mark job `processing`
  2. Load file from shared volume
  3. Extract raw text:
     - PDF: `pypdf` (simple, no OCR — assume digital-native PDFs for MVP; document OCR fallback with `pytesseract` as next step)
     - DOCX: `python-docx`
  4. Call Groq LLM with a structured-output prompt. Use Groq's JSON mode if available, otherwise prompt for JSON and validate with Pydantic
  5. Parse response into `ResumeExtraction`
  6. Save to MongoDB, mark job `completed`
  7. On any error: mark job `failed`, store error message, don't crash the worker
- Retry policy: 3 retries with exponential backoff for transient LLM errors
- LLM provider abstraction: `LLMProvider` base class with `GroqProvider` implementation — same pattern as PromptVault
- Tests: mock LLM response, verify happy path + PDF parsing + DOCX parsing + error path + retry behavior

**Done when:** A full upload → text extract → LLM call → structured JSON flow works end to end against the real Groq free tier.

---

## Phase 5 — Angular frontend scaffold

**Goal:** Angular 17+ with standalone components, routing, auth.

**Tasks:**
- `ng new frontend --standalone --routing --style=scss`
- Tailwind CSS installed (Angular 17+ supports it natively)
- Routes: `/login`, `/register`, `/documents` (list), `/documents/:id` (detail), `/upload`
- `AuthService` storing tokens in `localStorage` with `BehaviorSubject<User>`
- `AuthInterceptor` attaching JWT, handling 401 refresh
- `AuthGuard` protecting all routes except `/login` and `/register`
- Base layout with nav bar
- API service using Angular `HttpClient`, baseURL points to gateway

**Done when:** Register + login works against the gateway, protected routes enforce auth.

---

## Phase 6 — Upload UI

**Goal:** Drag-and-drop file upload with clear feedback.

**Tasks:**
- `/upload` page with:
  - Drag-and-drop zone (use a small library like `ngx-dropzone` or build it natively with Angular CDK)
  - File type validation client-side (PDF/DOCX only)
  - File size indicator, max 5MB enforced
  - Upload button with progress bar (use `HttpClient` upload progress events)
  - On success: redirect to `/documents/:id`
  - Error handling: server errors shown inline

**Done when:** Upload a PDF, see progress, get redirected to the detail page.

---

## Phase 7 — Documents list + status polling

**Goal:** See all uploaded documents, their processing status, and live updates.

**Tasks:**
- `/documents` page: table with filename, uploaded date, status badge (pending/processing/completed/failed), action buttons (view/delete)
- Status badges: colored chips with appropriate icons
- Polling: when any document has non-terminal status, poll `/api/documents/` every 2s until all settled. Stop polling when all documents are in a terminal state. Use RxJS `timer` + `switchMap`.
- Empty state: "No documents yet — upload your first resume"
- Delete with confirmation dialog

**Done when:** You upload a resume and watch its status transition pending → processing → completed without refreshing.

---

## Phase 8 — Document detail view (the money shot)

**Goal:** Pretty, structured display of the extracted resume data.

**Tasks:**
- `/documents/:id` page:
  - Header: filename, upload date, status, re-run extraction button (triggers new job)
  - If `completed`: render the `ResumeExtraction` nicely:
    - Candidate header card (name, email, phone, location)
    - Summary section
    - Skills as chips
    - Experience timeline (cards per job, most recent first)
    - Education cards
    - "View raw JSON" toggle — shows the structured output for the demo's sake
  - If `processing`: spinner + "Extracting with AI..."
  - If `failed`: error message + retry button
  - Sidebar: document metadata (size, type, job ID)

**Done when:** Completed resume shows a clean, structured view that would look good in a screenshot.

---

## Phase 9 — Tests, CI/CD, Docker

**Goal:** Everything green, everything containerized.

**Tasks:**
- Backend tests: pytest per service, coverage target 70% on handlers and the extraction pipeline
- Frontend tests: Jasmine/Karma (default Angular) — cover auth flow, upload, and detail rendering
- `.github/workflows/ci.yml` with a job matrix:
  - `gateway` — ruff + pytest
  - `document` — ruff + pytest (with a MongoDB service container)
  - `worker` — ruff + pytest (with Redis service container)
  - `frontend` — eslint + build + test
- Each service has its own `Dockerfile`:
  - Python services: slim base, non-root user, multi-stage where it helps
  - Frontend: Node build stage + nginx serve stage
- `docker-compose.yml` orchestrates all of it:
  - `mongo`, `redis`, `gateway`, `document`, `worker`, `frontend`
  - Shared named volume `uploads` mounted into `document` and `worker`
  - Healthchecks on every service
  - `depends_on` with `condition: service_healthy`
- `.env.example` at root documenting all variables (JWT keys, Groq API key, Mongo URI, Redis URL)

**Done when:** Fresh clone → `cp .env.example .env` → `docker compose up` → working full stack.

---

## Phase 10 — README and polish

**Goal:** Repo presents professionally to any recruiter in 30 seconds.

**Tasks:**
- README structure:
  - One-paragraph pitch
  - Screenshot of the extracted resume view
  - **Mermaid architecture diagram** — show Gateway, Document service, Worker, MongoDB, Redis, LLM provider, Angular — with arrows labeled (HTTP, Celery task, DB write, LLM call). This is the strongest visual signal of microservices competency in a portfolio.
  - "Why microservices" section — explicit paragraph on the architectural judgment call, pointing out the genuine reasons (async workload has different scaling characteristics than request/response, LLM latency shouldn't block the API tier, workers can be scaled independently). This is the portfolio signal — every architecture decision should have an explainable reason.
  - Local setup (4 commands)
  - Tech stack breakdown per service
  - "What I'd add next" section: OCR fallback for scanned resumes, S3 storage, WebSocket status streaming, Kubernetes manifests, observability stack (OpenTelemetry + Jaeger), rate limiting, multi-provider LLM routing
  - Note on extensibility — how adding a new extraction type (invoice, contract) would plug in
- Tag `v0.1.0`
- Clean commit history

**Done when:** README makes someone want to `git clone`.

---

## Stretch goals (post-MVP)

- OCR fallback (pytesseract + pdf2image for scanned PDFs)
- WebSocket status updates instead of polling
- S3/MinIO storage swap
- Multi-LLM routing (OpenRouter alongside Groq) — triggers a story parallel to DeepAdvisor
- Admin dashboard with extraction accuracy metrics
- Export extracted data to JSON Resume schema

---

## Execution notes

- Phase 0-4 are backend-only. Don't start Angular until the API works end-to-end via Postman/curl. Debugging a broken frontend against a broken backend is the single most common failure mode in microservices portfolio projects.
- The LLM call in Phase 4 is the riskiest part — test it early with a real Groq API key before building UI around it.
- Keep each service's `pyproject.toml` minimal. Don't share dependencies unless they're genuinely shared (auth verification utils, the contracts package).
- When writing the Mermaid diagram, keep it under 8 nodes. Cleaner diagrams communicate better than complete ones.
