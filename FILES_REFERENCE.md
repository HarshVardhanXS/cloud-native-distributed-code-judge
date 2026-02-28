# Complete File Listing & Purpose

## Project Files Overview

### Core Application Files

#### `app.py` (Main Application)
- **Lines:** ~550
- **Purpose:** FastAPI application with all HTTP endpoints
- **Contents:**
  - Health check endpoint
  - User registration & login endpoints
  - Problem management endpoints (CRUD)
  - Code submission endpoints
  - User statistics endpoint
  - CORS middleware configuration
  - Lifespan management
- **Key Classes:** FastAPI app instance
- **Key Functions:** All API route handlers

#### `models.py` (Database Models)
- **Lines:** ~60
- **Purpose:** SQLAlchemy ORM model definitions
- **Contains:**
  - `User` model - username, email, hashed_password, created_at, is_active
  - `Problem` model - title, description, difficulty, test_cases, creator_id
  - `Submission` model - user_id, problem_id, code, status, result
  - Relationships between models (foreign keys)
- **Database Tables Created:** Users, Problems, Submissions

#### `database.py` (Database Setup)
- **Lines:** ~25
- **Purpose:** Database configuration and connection management
- **Contains:**
  - SQLite connection URL configuration
  - SQLAlchemy engine setup
  - Session factory (SessionLocal)
  - Database initialization function
  - Dependency provider for DB sessions
- **Notes:** Uses `check_same_thread=False` for SQLite compatibility

#### `schemas.py` (Data Validation)
- **Lines:** ~90
- **Purpose:** Pydantic request/response schemas for data validation
- **Contains:**
  - `UserBase`, `UserCreate`, `UserResponse` - User operations
  - `Token` - JWT token response
  - `ProblemBase`, `ProblemCreate`, `ProblemUpdate`, `ProblemResponse` - Problem operations
  - `SubmissionBase`, `SubmissionCreate`, `SubmissionResponse` - Submission operations
  - Email validation for user registration
- **Features:** Auto-generated OpenAPI schema from these models

#### `auth.py` (Authentication & Security)
- **Lines:** ~65
- **Purpose:** JWT and password management utilities
- **Contains:**
  - `verify_password()` - Bcrypt password verification
  - `get_password_hash()` - Bcrypt password hashing
  - `create_access_token()` - JWT token generation
  - `get_current_username_from_token()` - JWT validation
  - OAuth2 Bearer scheme configuration
- **Configuration:**
  - DEFAULT: Uses `SECRET_KEY` from environment (fallback: weak default for testing)
  - Token expiration: 30 minutes
  - Algorithm: HS256

#### `judge.py` (Code Execution Engine)
- **Lines:** ~165
- **Purpose:** Code execution in Docker sandbox with fallbacks
- **Contains:**
  - `execute_code()` - Docker-based execution (primary)
  - `execute_code_sync()` - Synchronous execution with Docker fallback
  - Test case parsing and validation
  - Result comparison and formatting
- **Safety Features:**
  - Memory limit: 256MB
  - CPU limit: 0.5 cores
  - Timeout: 10 seconds per test
  - Auto container cleanup (--rm)
  - Graceful fallback to mock execution if Docker unavailable

### Configuration & Deployment Files

#### `requirements.txt` (Python Dependencies)
- **Lines:** 11
- **Packages:** 10 core dependencies
  - `fastapi==0.104.1`
  - `uvicorn[standard]==0.24.0`
  - `pydantic==2.5.0`
  - `pydantic-settings==2.1.0`
  - `email-validator==2.1.0`
  - `sqlalchemy==2.0.23`
  - `python-jose[cryptography]==3.3.0`
  - `passlib==1.7.4`
  - `bcrypt==4.1.2`
  - `python-multipart==0.0.6`
  - `pytest==7.4.3`
  - `httpx==0.25.2`
- **Total Size:** ~100MB when installed with deps

#### `Dockerfile` (Container Configuration)
- **Lines:** ~40
- **Base Image:** `python:3.11-slim` (~150MB)
- **Stages:**
  1. Install system dependencies (Docker CLI, curl)
  2. Create non-root user (`judge:judge`)
  3. Copy requirements and install Python dependencies
  4. Copy application files
  5. Set ownership to non-root user
  6. Expose port 8000
  7. Configure health check
  8. Run application
- **Security:** Non-root user execution
- **Health Check:** Uses `/health` endpoint with 30s interval

#### `azure_deploy.sh` (Azure Automation)
- **Lines:** ~400
- **Purpose:** Interactive script for complete Azure deployment
- **Performs:**
  1. Prerequisite checks (Azure CLI, Docker)
  2. User configuration input (subscription, location, names)
  3. Azure login and authentication
  4. Resource group creation
  5. Container Registry (ACR) creation
  6. Docker image building and pushing to ACR
  7. App Service plan creation
  8. Web app deployment
  9. Container registry configuration
  10. Application settings configuration
  11. Optional Azure Container Instances deployment
  12. Summary and next steps
- **Output:** Deployment summary with URLs and monitoring commands

### Documentation Files

#### `README.md` (Main Documentation)
- **Lines:** ~600
- **Sections:**
  - Project overview and features
  - Architecture diagram
  - Quick start guide
  - API endpoint reference
  - Example usage with curl commands
  - Database schema documentation
  - Code execution sandbox explanation
  - Docker deployment instructions
  - Azure deployment (manual) instructions
  - Performance considerations
  - Security features and recommendations
  - Troubleshooting guide
  - Contributing guidelines
  - Roadmap

#### `RUNNING.md` (Deployment & Execution Guide)
- **Lines:** ~500
- **Sections:**
  - Local development setup (3 steps)
  - Docker deployment (build, run, stop)
  - Azure automated deployment (`./azure_deploy.sh`)
  - Azure manual deployment (7 detailed steps)
  - Azure Container Instances deployment
  - Environment variables reference
  - Troubleshooting common issues
  - Performance tips
  - Security recommendations
  - Next steps

#### `DEPLOYMENT_SUMMARY.md` (High-Level Overview)
- **Lines:** ~400
- **Contents:**
  - Project overview
  - What was built (components)
  - Quick start (60 seconds)
  - Key features summary
  - API endpoints table
  - Architecture decisions and rationale
  - Performance characteristics
  - Security features and recommendations
  - File manifest
  - What's not included (by design)
  - Scaling considerations
  - Next steps and support

#### `ARCHITECTURE.md` (Visual Architecture)
- **Lines:** ~500
- **Contents:**
  - System architecture diagram (ASCII)
  - Deployment architecture diagrams (3 variations)
    - Local Codespaces
    - Docker
    - Azure Cloud
  - Data flow diagrams
    - User registration
    - Code submission
    - Docker execution
  - Technology stack breakdown
  - Dependency graph
  - Database schema ER diagram
  - Request-response cycle flow

### Testing & Utility Files

#### `test_api.sh` (API Test Script)
- **Lines:** ~70
- **Purpose:** Comprehensive API testing script
- **Tests:**
  1. Health check
  2. User login and JWT generation
  3. Current user profile retrieval
  4. Problem creation
  5. Problem listing
  6. Code submission
  7. Submission listing
  8. User statistics
- **Usage:** `./test_api.sh` after starting application

#### `.gitignore` (Git Configuration)
- **Lines:** ~50
- **Ignores:**
  - Python: `__pycache__/`, `*.pyc`, `venv/`, `.venv`
  - Database: `*.db`, `*.sqlite`, `*.sqlite3`
  - IDE: `.vscode/`, `.idea/`
  - Environment: `.env*`
  - Testing: `.pytest_cache/`, `.coverage`
  - Azure: `.azure/`
  - Logs: `*.log`
  - OS: `.DS_Store`

### Runtime Generated Files

#### `judge.db` (SQLite Database)
- **Purpose:** Local persistent data storage
- **Created:** Automatically on first application run
- **Size:** ~1MB typical (grows with submissions)
- **Tables:** Users, Problems, Submissions
- **Location:** Root project directory
- **Deletion:** Safe to delete and recreate (`rm judge.db`)

### Project Structure Summary

```
cloud-native-distributed-code-judge/
│
├── Core Application
│   ├── app.py              # Main FastAPI application
│   ├── models.py           # SQLAlchemy ORM models
│   ├── database.py         # Database configuration
│   ├── schemas.py          # Pydantic validation schemas
│   ├── auth.py             # JWT & password utilities
│   └── judge.py            # Code execution engine
│
├── Configuration & Deployment
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile          # Container configuration
│   ├── azure_deploy.sh     # Azure automation script
│   └── .gitignore          # Git ignore rules
│
├── Documentation
│   ├── README.md           # Main comprehensive guide
│   ├── RUNNING.md          # Execution & deployment guide
│   ├── DEPLOYMENT_SUMMARY.md  # High-level overview
│   └── ARCHITECTURE.md     # Visual architecture diagrams
│
├── Testing
│   └── test_api.sh         # API test script
│
├── Runtime Generated
│   ├── judge.db            # SQLite database
│   └── __pycache__/        # Python cache
│
└── Git
    └── .git/               # Version control
```

## File Size Summary

| File | Size | Type |
|------|------|------|
| app.py | ~15KB | Python |
| models.py | ~2KB | Python |
| database.py | ~1KB | Python |
| schemas.py | ~3KB | Python |
| auth.py | ~2KB | Python |
| judge.py | ~6KB | Python |
| requirements.txt | <1KB | Text |
| Dockerfile | ~1KB | Docker |
| azure_deploy.sh | ~13KB | Bash |
| test_api.sh | ~2KB | Bash |
| README.md | ~20KB | Markdown |
| RUNNING.md | ~15KB | Markdown |
| DEPLOYMENT_SUMMARY.md | ~12KB | Markdown |
| ARCHITECTURE.md | ~15KB | Markdown |

**Total Source Code:** ~110KB
**Total Documentation:** ~60KB
**Total (without venv, .git, __pycache__):** ~170KB

## Dependencies Map

```
Installation Requirements:
├── fastapi (HTTP framework) → starlette, pydantic
├── uvicorn (ASGI server) → httptools, websockets
├── pydantic (validation) → email-validator (optional)
├── sqlalchemy (ORM) → greenlet
├── python-jose (JWT) → cryptography, rsa
├── passlib (password hashing interface)
├── bcrypt (password hashing algorithm)
└── pytest (testing) → pluggy
```

## Runtime Requirements

### Local Development
- **Python:** 3.11+
- **Memory:** 200MB (app + Python interpreter)
- **Disk:** 100MB (app + dependencies)
- **Docker:** Required for code sandbox (optional with fallback)

### Docker Container
- **Base Image:** python:3.11-slim (~150MB)
- **Image Size:** ~180MB (with dependencies)
- **Runtime Memory:** 100-200MB normal operation
- **Startup Time:** ~5 seconds

### Azure App Service
- **Plan:** B1 (1 vCPU, 1.75GB RAM)
- **Cost:** ~$10-15/month
- **Scaling:** Can upgrade to S1/S2 for higher traffic
- **Storage:** 1GB includes database

## Configuration Options

### Environment Variables
```
SECRET_KEY              # JWT signing key (MUST change in production)
DATABASE_URL            # SQLite path (default: sqlite:///./judge.db)
DEBUG                   # FastAPI debug mode (default: false)
LOG_LEVEL              # Logging level (default: INFO)
```

### Hardcoded Configuration
```python
# auth.py
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = "HS256"

# judge.py
TIMEOUT_SECONDS = 10
MEMORY_LIMIT_MB = 256
CPU_LIMIT = 0.5
```

## Making Changes

### Add New API Endpoint
1. Add route handler in `app.py`
2. Add request/response schema in `schemas.py`
3. Test with Swagger UI (`/docs`)

### Add Database Field
1. Modify model in `models.py`
2. SQLAlchemy will handle schema updates (recreate DB if needed)
3. Update related schemas in `schemas.py`

### Change Code Execution Settings
1. Edit `judge.py` constants
2. Restart application
3. Test with `test_api.sh`

### Deploy to New Azure Region
1. Edit `azure_deploy.sh` or run with different location input
2. Resources will be created in chosen region

## Testing Checklist

- [ ] `python app.py` starts without errors
- [ ] Swagger UI accessible at `/docs`
- [ ] `./test_api.sh` passes all tests
- [ ] `docker build -t test .` succeeds
- [ ] `docker run` container works locally
- [ ] `./azure_deploy.sh` completes deployment
- [ ] Post-deployment health check returns 200

---

*Complete file reference for Cloud-Native Code Judge Project*
