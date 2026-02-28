# Architecture & Component Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud-Native Code Judge                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         FastAPI Application (Single Service)            │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │         HTTP API Endpoints                         │  │  │
│  │  │  • /register (User management)                     │  │  │
│  │  │  • /token (JWT authentication)                     │  │  │
│  │  │  • /problems (Problem CRUD)                        │  │  │
│  │  │  • /submissions (Solution submission & tracking)   │  │  │
│  │  │  • /stats (User statistics)                        │  │  │
│  │  │  • /health (Monitoring)                            │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         ↑                                  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │    Authentication & Authorization (JWT)           │  │  │
│  │  │  • Password hashing (bcrypt)                       │  │  │
│  │  │  • Token generation & validation                   │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         ↓                                  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │    Code Judge & Execution Engine                  │  │  │
│  │  │  • Docker sandbox execution                        │  │  │
│  │  │  • Test case validation                            │  │  │
│  │  │  • Result storage                                  │  │  │
│  │  │  • Mock execution fallback                         │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         ↓                                  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │    SQLAlchemy ORM Layer                            │  │  │
│  │  │  • Users table                                      │  │  │
│  │  │  • Problems table                                   │  │  │
│  │  │  • Submissions table                                │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│           ↓                                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      SQLite Database (judge.db)                        │  │
│  │                                                           │  │
│  │  [Users]  [Problems]  [Submissions]                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      Docker Sandbox (Code Execution)                    │  │
│  │                                                           │  │
│  │  docker run --rm python:3.11-slim                        │  │
│  │  • Memory limit: 256MB                                  │  │
│  │  • CPU limit: 0.5 cores                                 │  │
│  │  • Timeout: 10 seconds                                  │  │
│  │  • Auto-cleanup                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architectures

### Local Development (Codespaces)
```
┌─────────────────────────────────┐
│     GitHub Codespaces           │
│                                 │
│  ┌─────────────────────────┐   │
│  │  Python 3.11 (fast)     │   │
│  │  • FastAPI app.py       │   │
│  │  • SQLite judge.db      │   │
│  │  • Docker CLI (DinD)    │   │
│  └─────────────────────────┘   │
│  Port 8000 (Forwarded)          │
│                                 │
│  Memory: ~200MB total           │
│  Disk: < 50MB app + deps        │
└─────────────────────────────────┘
```

### Docker (Local Testing)
```
    Docker Host
    ┌─────────────────────────────────────────┐
    │                                         │
    │  ┌──────────────────────────────────┐   │
    │  │  code-judge Container            │   │
    │  │  (python:3.11-slim)              │   │
    │  │                                   │   │
    │  │  • FastAPI app.py                 │   │
    │  │  • SQLite judge.db                │   │
    │  │  • Docker client                  │   │
    │  │  • Non-root user (judge:judge)    │   │
    │  │                                   │   │
    │  │  Port 8000                        │   │
    │  └──────────────────────────────────┘   │
    │             ↓                           │
    │  ┌──────────────────────────────────┐   │
    │  │  Code Execution Containers       │   │
    │  │  (python:3.11-slim)              │   │
    │  │  (Created on demand, ephemeral)  │   │
    │  └──────────────────────────────────┘   │
    │                                         │
    └─────────────────────────────────────────┘
```

### Azure Deployment (Production)
```
┌──────────────────────────────────────────────────────────────┐
│                    Azure Cloud                               │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Azure Container Registry (ACR)                    │   │
│  │    myjudgeregistry.azurecr.io                        │   │
│  │    • Stores: code-judge:latest                       │   │
│  └──────────────────────────────────────────────────────┘   │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Azure App Service (Linux)                         │   │
│  │    my-code-judge.azurewebsites.net                   │   │
│  │                                                       │   │
│  │  • Web App Container Instance                         │   │
│  │  • Health Check Enabled                              │   │
│  │  • Auto-restart on failure                           │   │
│  │  • HTTPS (automatic)                                 │   │
│  │  • Scaling: B1 plan (1 vCPU, 1.75GB RAM)             │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────┐            │   │
│  │  │  FastAPI Container                   │            │   │
│  │  │  • SQLite Database (local storage)    │            │   │
│  │  │  • Docker client for sandboxing       │            │   │
│  │  └──────────────────────────────────────┘            │   │
│  └──────────────────────────────────────────────────────┘   │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Optional: Azure Container Instances (ACI)        │   │
│  │    code-judge-aci.eastus.azurecontainer.io           │   │
│  │    • For high concurrency code execution             │   │
│  │    • Separate from main app                          │   │
│  │    • Scales independently                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### User Registration Flow
```
Client                                      Server
  │                                           │
  ├──────────── POST /register ──────────────→│
  │            (username, email, password)    │
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Validate     │
  │                                    │ Input        │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Hash         │
  │                                    │ Password     │
  │                                    │ (bcrypt)     │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Store in     │
  │                                    │ SQLite       │
  │                                    └──────┬───────┘
  │                                           │
  │←───────── 200 OK + User ID ────────────┤
```

### Code Submission & Execution Flow
```
Client                                      Server
  │                                           │
  ├──────── POST /problems/1/submit ────────→│
  │      (code + JWT token)                   │
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Validate     │
  │                                    │ JWT token    │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Get problem  │
  │                                    │ & test cases │
  │                                    │ from SQLite  │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Execute code │
  │                                    │ in Docker    │
  │                                    │ sandbox      │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Compare      │
  │                                    │ results vs   │
  │                                    │ expected     │
  │                                    └──────┬───────┘
  │                                           │
  │                                    ┌──────▼───────┐
  │                                    │ Store        │
  │                                    │ submission   │
  │                                    │ in SQLite    │
  │                                    └──────┬───────┘
  │                                           │
  │←── 201 Created + Submission ID ────────┤
  │    (with status & results)                │
```

### Code Execution in Docker
```
FastAPI App          Docker Daemon           Container
     │                   │                        │
     ├──── Create ──────→ │                        │
     │   Container       │                        │
     │             ┌─────▼─────┐                 │
     │             │ Start New │                 │
     │             │ python:   │                 │
     │             │ 3.11-slim │                 │
     │             │ Container │                 │
     │             └─────┬─────┘                 │
     │                   │        ┌──────────────▼─┐
     │                   │        │ Run Python     │
     │                   │        │ code with test │
     │                   │        │ cases          │
     │                   │        └──────────────┬─┘
     │                   │                       │
     │←── Capture ──────┤←── Output stdout ────┤│
     │   stdout/stderr  │                       │
     │             ┌─────▼─────┐                 │
     │             │ Container │                 │
     │             │ Cleanup   │                 │
     │             │ (--rm)    │                 │
     │             └───────────┘                 │
     │                                            │
     ├─ Parse results ─→                        │
     │ Compare expected vs actual                │
     │ Store to SQLite                          │
```

## Technology Stack

```
┌──────────────────────────────────────────────────────────┐
│                   Technology Stack                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Languages & Runtime                                    │
│  ├─ Python 3.11                                         │
│  └─ SQLite 3                                            │
│                                                          │
│  Backend Framework                                      │
│  ├─ FastAPI 0.104.1 (async REST API)                   │
│  ├─ Uvicorn 0.24.0 (ASGI server)                       │
│  └─ Pydantic 2.5.0 (data validation)                   │
│                                                          │
│  Database & ORM                                         │
│  ├─ SQLite (file-based, no server)                     │
│  ├─ SQLAlchemy 2.0.23 (ORM)                            │
│  └─ Alembic (migrations - optional)                    │
│                                                          │
│  Security                                               │
│  ├─ python-jose (JWT tokens)                           │
│  ├─ passlib (password hashing interface)               │
│  ├─ bcrypt (password hashing algorithm)                │
│  └─ cryptography (encryption)                          │
│                                                          │
│  Code Execution                                         │
│  └─ Docker CLI (sandbox execution)                     │
│     python:3.11-slim (execution base image)            │
│                                                          │
│  Testing & Documentation                               │
│  ├─ Pytest                                             │
│  └─ httpx (async HTTP client)                         │
│                                                          │
│  Containerization                                       │
│  ├─ Docker (local testing, deployment)                │
│  └─ Docker Hub (python:3.11-slim image)               │
│                                                          │
│  Cloud Deployment                                       │
│  ├─ Azure Container Registry                           │
│  ├─ Azure App Service                                  │
│  └─ Azure Container Instances (optional)               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Dependency Graph

```
FastAPI App
├── fastapi (HTTP framework)
├── uvicorn (ASGI server)
├── pydantic (validation)
│   └── email-validator
├── sqlalchemy (ORM)
├── python-jose (JWT)
│   └── cryptography
├── passlib (password hashing)
│   ├── bcrypt
│   └── cryptography
├── python-multipart (form parsing)
└── pytest, httpx (testing)
```

## Database Schema

```
┌─────────────────────┐
│      Users          │
├─────────────────────┤
│ id (PK)             │
│ username (UNIQUE)   │
│ email (UNIQUE)      │
│ hashed_password     │
│ created_at          │
│ is_active           │
└─────────────────────┘
        ↓
  (creator_id) ←──────────────────┐
        │                         │
        │                  ┌──────▼──────────┐
        │                  │    Problems     │
        │                  ├─────────────────┤
        │                  │ id (PK)         │
        │                  │ title           │
        │                  │ description     │
        │                  │ difficulty      │
        │                  │ test_cases(JSON)│
        │                  │ creator_id (FK) │
        │                  │ created_at      │
        │                  │ updated_at      │
        │                  └─────────────────┘
        │                         ↓
        │                  (problem_id) ←─────────┐
        │                                           │
        └──────────────────────┐ ┌────────────────▼──┐
                               │─┤  Submissions       │
                                 ├────────────────────┤
                                 │ id (PK)            │
                                 │ user_id (FK)       │
                                 │ problem_id (FK)    │
                                 │ code (TEXT)        │
                                 │ status (pending,   │
                                 │         passed,    │
                                 │         failed)    │
                                 │ result (JSON)      │
                                 │ created_at         │
                                 └────────────────────┘
```

## Request-Response Cycle

```
HTTP Request
    ↓
┌─── FastAPI Routing ─────┐
│                         │
├─ URL matching           │
├─ Path parameter parsing │
└─────────┬───────────────┘
          ↓
┌─────────────────────────┐
│ Dependency Injection    │
├─────────────────────────┤
│ • Get DB session        │
│ • Extract JWT token     │
│ • Retrieve current user │
└─────────┬───────────────┘
          ↓
┌─────────────────────────┐
│ Request Validation      │
├─────────────────────────┤
│ Pydantic schema check   │
│ Email validation (if    │
│ applicable)             │
└─────────┬───────────────┘
          ↓
┌─────────────────────────┐
│ Endpoint Handler        │
├─────────────────────────┤
│ • Business logic        │
│ • DB operations         │
│ • Authorization checks  │
└─────────┬───────────────┘
          ↓
┌─────────────────────────┐
│ Response Serialization  │
├─────────────────────────┤
│ Pydantic model to JSON  │
└─────────┬───────────────┘
          ↓
HTTP Response (JSON)
    ↓
Client
```

---

*Diagrams illustrate key architectural decisions and data flows*
