# Cloud-Native Distributed Code Judge

A lightweight, cloud-based system design playground combining LeetCode-style problems with a code judge, built for deployment on Azure and local development in GitHub Codespaces.

## Features

✨ **Core Features**
- 🔐 JWT-based authentication
- 📝 Create and manage coding problems
- 🚀 Submit and test solutions
- 📊 Track submission history
- 🏃 Async code execution in Docker sandbox
- 📈 User statistics and progress tracking
- 🏥 Health check endpoint for monitoring

✅ **Production Ready**
- Lightweight design optimized for Codespaces
- Single FastAPI backend service
- SQLite database with SQLAlchemy ORM
- Docker containerization (Python 3.11-slim)
- Non-root user execution
- Azure-ready deployment scripts

## Deployment Platforms

This project is deployed and maintained across:

- **Azure**: cloud deployment and execution infrastructure (App Service / ACI / ACR workflow via `azure_deploy.sh`).
- **Docker**: containerized runtime for local and cloud parity (`Dockerfile`, `docker-compose.yml`).
- **GitHub**: source repository, issue tracking, and collaboration workflow.

## Architecture

```mermaid
flowchart LR
    U[Users / Browser] --> F[Next.js Frontend]
    F --> B[FastAPI Backend]
    B --> DB[(PostgreSQL / SQLite)]
    B --> R[(Redis - optional)]
    B --> Q[Celery Queue]
    Q --> W[Execution Worker]
    W --> X[Azure ACI or Local Fallback Executor]
    B --> L[Leaderboard Aggregation]
    L --> DB
```

## Request Flowchart

```mermaid
flowchart TD
    A[Open Dashboard] --> B[Load Problems + Leaderboard]
    B --> C[Open Problem Detail]
    C --> D[Fetch Description, Examples, Constraints, Answer Key]
    D --> E[Write Solution / Design Answer]
    E --> F[Submit]
    F --> G[Create Submission Record]
    G --> H[Execute Against Test Cases]
    H --> I[Persist Verdict, Runtime, Analytics Data]
    I --> J[Update History + Leaderboard + Discussions View]
```
## Project Structure

```
.
├── app.py                    # Main FastAPI application with all endpoints
├── models.py                 # SQLAlchemy database models
├── database.py              # Database initialization and connection
├── schemas.py               # Pydantic request/response schemas
├── auth.py                  # JWT authentication utilities
├── judge.py                 # Code execution and judging engine
├── requirements.txt         # Python dependencies
├── Dockerfile               # Production Docker image
├── azure_deploy.sh          # Azure deployment script
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Docker (for code execution sandbox)
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/HarshVardhanXS/cloud-native-distributed-code-judge.git
cd cloud-native-distributed-code-judge
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Access the API:
   - **Web:** http://localhost:8000
   - **Swagger UI:** http://localhost:8000/docs
   - **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### Authentication
- POST `/register` - Register a new user
- POST `/token` - Login and get JWT token
- GET `/me` - Get current user profile

### Problems
- GET `/problems` - List all problems
- GET `/problems/{id}` - Get a specific problem
- POST `/problems` - Create a new problem (authenticated)
- PUT `/problems/{id}` - Update a problem (creator only)

### Submissions
- POST `/problems/{id}/submit` - Submit solution to a problem
- GET `/submissions` - List user's submissions
- GET `/submissions/{id}` - Get a specific submission
- GET `/problems/{id}/submissions` - List submissions for a problem
- GET `/stats` - Get user statistics

### Health Check
- GET `/health` - Service health status

## Example Usage

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=securepassword123"
```

### 3. Create a Problem
```bash
TOKEN="your_access_token_here"

curl -X POST "http://localhost:8000/problems" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Two Sum",
    "description": "Find two numbers that add up to target",
    "difficulty": "easy",
    "test_cases": "[{\"input\": {\"nums\": [2, 7, 11], \"target\": 9}, \"output\": [0, 1]}]"
  }'
```

### 4. Submit a Solution
```bash
TOKEN="your_access_token_here"

curl -X POST "http://localhost:8000/problems/1/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []"
  }'
```

## Database Schema

### Users Table
- id (PRIMARY KEY)
- username (UNIQUE)
- email (UNIQUE)
- hashed_password
- created_at
- is_active

### Problems Table
- id (PRIMARY KEY)
- title
- description
- difficulty
- test_cases (JSON string)
- creator_id (FOREIGN KEY)
- created_at
- updated_at

### Submissions Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- problem_id (FOREIGN KEY)
- code
- status (pending/passed/failed/error)
- result (JSON output)
- created_at

## Code Execution Sandbox

Uses Docker with resource limits:
```bash
docker run --rm --memory=256m --cpus=0.5 python:3.11-slim python -c "your_code"
```

**Safety Features:**
- Memory limit: 256MB
- CPU limit: 0.5 cores
- Auto cleanup
- Timeout protection (10s)
- Isolated execution

## Docker Deployment

### Build Image
```bash
docker build -t code-judge:latest .
```

### Run Container
```bash
docker run -d \
  --name code-judge \
  -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  code-judge:latest
```

### Check Health
```bash
curl http://localhost:8000/health
```

## Azure Deployment

### Automated Deployment
```bash
chmod +x azure_deploy.sh
./azure_deploy.sh
```

This will:
- Create resource group
- Build and push image to ACR
- Create App Service plan
- Deploy web app
- Optionally deploy to Container Instances

### Manual Deployment

#### 1. Create Container Registry
```bash
az acr create \
  --resource-group my-rg \
  --name myjudgeregistry \
  --sku Basic
```

#### 2. Build and Push Image
```bash
az acr build \
  --registry myjudgeregistry \
  --image code-judge:latest .
```

#### 3. Create App Service
```bash
az appservice plan create \
  --name judge-plan \
  --resource-group my-rg \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group my-rg \
  --plan judge-plan \
  --name my-code-judge \
  --deployment-container-image-name myjudgeregistry.azurecr.io/code-judge:latest
```

#### 4. Configure Registry Access
```bash
az webapp config container set \
  --resource-group my-rg \
  --name my-code-judge \
  --docker-custom-image-name myjudgeregistry.azurecr.io/code-judge:latest \
  --docker-registry-server-url https://myjudgeregistry.azurecr.io \
  --docker-registry-server-user <username> \
  --docker-registry-server-password <password>
```

#### 5. Set Environment Variables
```bash
az webapp config appsettings set \
  --resource-group my-rg \
  --name my-code-judge \
  --settings \
    WEBSITES_PORT=8000 \
    SECRET_KEY="$(openssl rand -hex 32)"
```

### Access Deployed Application
- **URL:** https://my-code-judge.azurewebsites.net
- **API Docs:** https://my-code-judge.azurewebsites.net/docs
- **Health:** https://my-code-judge.azurewebsites.net/health

### Container Instances Deployment
```bash
az container create \
  --resource-group my-rg \
  --name code-judge-aci \
  --image myjudgeregistry.azurecr.io/code-judge:latest \
  --cpu 1 \
  --memory 1 \
  --port 8000 \
  --dns-name-label code-judge-demo \
  --registry-login-server myjudgeregistry.azurecr.io \
  --registry-username <username> \
  --registry-password <password>
```

Access: http://code-judge-demo.eastus.azurecontainer.io:8000

## Vercel Deployment

Deploy this monorepo as two Vercel projects:

1) **Backend API project** (root directory: repository root)
- Framework preset: `Other`
- Build uses `vercel.json` + `api/index.py` (FastAPI serverless entrypoint)
- Required env vars:
  - `DATABASE_URL` (PostgreSQL recommended on Vercel)
  - `SECRET_KEY` (32+ chars)
- Optional env vars:
  - `REDIS_URL` (for true async Celery workers/caching; without it Celery runs eager/in-process)
  - `AZURE_SUBSCRIPTION_ID`
  - `AZURE_EXECUTION_RESOURCE_GROUP`
  - `AZURE_LOCATION`
  - `AZURE_EXECUTION_IMAGE`
  - `AZURE_EXECUTION_REGISTRY_SERVER`
  - `AZURE_EXECUTION_REGISTRY_USERNAME`
  - `AZURE_EXECUTION_REGISTRY_PASSWORD`
  - `LOCAL_EXECUTION_TIMEOUT_SECONDS` (default `8`; used by local fallback executor when ACI is unavailable)

Submission execution behavior:
- If Azure ACI settings are configured and Azure CLI is available, submissions run in ACI.
- Otherwise, the API falls back to local subprocess execution (functional, but not equivalent to a hardened sandbox).

2) **Frontend project** (root directory: `cloudjudge-frontend`)
- Framework preset: `Next.js`
- Required env var:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-backend-vercel-domain>`

3) **CORS on backend**
- Set `CORS_ORIGINS` to your frontend URL, for example:
  - `https://your-frontend.vercel.app`
  - Multiple allowed origins can be comma-separated.

## Environment Variables

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://username:password@hostname:5432/database?sslmode=require
REDIS_URL=rediss://:password@host:6380/0
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
AZURE_SUBSCRIPTION_ID=
AZURE_EXECUTION_RESOURCE_GROUP=
AZURE_LOCATION=
LOCAL_EXECUTION_TIMEOUT_SECONDS=8
```

## Performance

### Memory Usage
- Application: ~100MB
- Database: ~1MB
- Per Sandbox: ~20MB

### Optimizations
- Minimal dependencies
- SQLite for light persistence
- Docker with resource limits
- Connection pooling

## Security Features

✅ **Implemented:**
- Password hashing (bcrypt)
- JWT authentication
- CORS protection
- SQL injection prevention (ORM)
- Non-root Docker user
- Resource limits on execution

⚠️ **Production Recommendations:**
- Change SECRET_KEY
- Use HTTPS only
- Implement rate limiting
- Monitor sandbox execution
- Regular security updates

## Troubleshooting

### Docker Not Available
```
Error: docker: not found
Solution: Install Docker or ensure daemon running
```

### Port in Use
```
Error: Address already in use
Solution: Use different port - python -c "import uvicorn; uvicorn.run('app:app', port=8001)"
```

### Database Locked
```
Error: database is locked
Solution: rm judge.db && python app.py
```

## Testing

```bash
pytest
```

Use Swagger UI at http://localhost:8000/docs

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Authors

- **Harsh Vardhan** - [GitHub](https://github.com/HarshVardhanXS)

## Roadmap

- [ ] WebSocket support for real-time execution
- [ ] Multiple language support (Java, C++, JavaScript)
- [ ] Problem difficulty rankings
- [ ] Discussion/solution sharing
- [ ] Timed contests
- [ ] Admin dashboard
- [ ] Performance analytics

## Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for cloud-native development**
