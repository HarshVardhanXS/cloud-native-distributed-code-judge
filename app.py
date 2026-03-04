from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timedelta
import logging
import os
import json
from typing import Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import (
    AZURE_EXECUTION_RESOURCE_GROUP,
    AZURE_LOCATION,
    AZURE_SUBSCRIPTION_ID,
)
from database import init_db, get_db
from models import User, Problem, Submission, TestCase, Discussion
from schemas import (
    UserCreate, UserResponse, Token,
    ProblemCreate, ProblemResponse, ProblemUpdate,
    SubmissionCreate, SubmissionResponse, SubmissionWithProblem,
    TestCaseCreate, TestCaseResponse, LeaderboardEntry,
    DiscussionCreate, DiscussionResponse,
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_username_from_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from tasks import execute_submission

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_ = (
    AZURE_SUBSCRIPTION_ID,
    AZURE_EXECUTION_RESOURCE_GROUP,
    AZURE_LOCATION,
)


# Configure CORS origins from environment
def get_cors_origins() -> list[str]:
    """
    Get CORS origins from environment variable.
    
    CORS_ORIGINS env var should be comma-separated list of origins.
    Defaults to http://localhost:3000 for development.
    
    Examples:
        - http://localhost:3000
        - http://localhost:3000,https://example.com
        - https://app.example.com,https://staging.example.com
    """
    origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    return origins


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_ok = init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable; app started in degraded mode")
    
    # Log CORS configuration
    cors_origins = get_cors_origins()
    logger.info(f"CORS enabled for {len(cors_origins)} origin(s):")
    for origin in cors_origins:
        logger.info(f"  - {origin}")
    
    yield
    # Shutdown
    logger.info("Application shutting down")


# Initialize app
app = FastAPI(
    title="Cloud-Native Code Judge",
    description="Lightweight cloud-based code judging system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - configured from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint for Azure deployment"""
    return {
        "status": "healthy",
        "service": "Cloud-Native Code Judge"
    }


# ==================== Authentication ====================

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    db_email = db.query(User).filter(User.email == user.email).first()
    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"User registered: {user.username}")
    return db_user


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get JWT token"""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserResponse)
async def get_current_user_info(
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


@app.delete("/me")
async def delete_my_account(
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db),
):
    """Delete current user account and all owned submissions."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    db.query(Submission).filter(Submission.user_id == user.id).delete()
    db.delete(user)
    db.commit()

    return {"message": "Account deleted successfully"}


# ==================== Problems ====================

@app.get("/api/problems", response_model=list[ProblemResponse])
async def list_problems_api(
    difficulty: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """List all problems with optional difficulty/tags filtering."""
    query = db.query(Problem).order_by(Problem.id.asc())

    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    problems = query.all()

    if tags:
        requested_tags = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}
        if requested_tags:
            problems = [
                problem for problem in problems
                if problem.tags and any(
                    isinstance(problem_tag, str) and problem_tag.lower() in requested_tags
                    for problem_tag in problem.tags
                )
            ]

    return problems


@app.get("/api/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem_api(problem_id: int, db: Session = Depends(get_db)):
    """Get one problem by id."""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    return problem


def _is_system_design_problem(problem: Problem) -> bool:
    tags = [tag.lower() for tag in (problem.tags or []) if isinstance(tag, str)]
    return "system design" in tags or "architecture" in tags


def _build_problem_details(problem: Problem, testcases: list[TestCase]) -> dict[str, Any]:
    examples = [
        {"input": testcase.input_data, "output": testcase.expected_output}
        for testcase in testcases[:4]
    ]
    is_sd = _is_system_design_problem(problem)

    if is_sd:
        return {
            "problem_type": "system_design",
            "supported_languages": ["Design Doc", "Markdown", "Python", "JavaScript", "Java", "C++"],
            "constraints": [
                "Prioritize availability over strict consistency unless stated otherwise.",
                "Target p95 response under 200ms for read-heavy endpoints.",
                "Design to scale to 100,000 concurrent users during peak events.",
                "Assume regional failures and include graceful degradation.",
            ],
            "requirements": {
                "functional": [
                    "Users should browse and open a problem statement.",
                    "Users should submit a structured design answer.",
                    "Users should view discussion and leaderboard context.",
                    "System should support competition-style ranking.",
                ],
                "non_functional": [
                    "High availability and secure isolation for code execution.",
                    "End-to-end observability with metrics and logs.",
                    "Scalable storage and queue-based processing.",
                    "Low operational complexity for moderate scale.",
                ],
            },
            "diagram_tools": [
                "Client",
                "CDN",
                "API Gateway",
                "Load Balancer",
                "Service",
                "Database",
                "Cache",
                "Queue",
                "Object Storage",
                "Monitoring",
            ],
            "answer_key": {
                "approach": (
                    "Start with requirements, define entities, and map APIs one-by-one to components. "
                    "Use API servers + primary datastore + cache + async queue/workers for heavy tasks. "
                    "Introduce horizontal scaling, failure isolation, and periodic leaderboard materialization."
                ),
                "high_level_components": [
                    "Web/App Client",
                    "API Gateway + Auth middleware",
                    "Problem Service",
                    "Submission Service + Queue + Workers",
                    "Leaderboard Service + Redis sorted sets",
                    "Primary DB + Object storage + Metrics/Logs stack",
                ],
                "tradeoffs": [
                    "Polling leaderboard every 5s is simpler than websockets at moderate scale.",
                    "Queue introduces slight latency but improves reliability and backpressure control.",
                    "Caching reduces DB load but requires invalidation strategy.",
                ],
            },
            "examples": examples,
        }

    return {
        "problem_type": "coding",
        "supported_languages": ["Python", "JavaScript", "Java", "C++"],
        "constraints": [
            "Optimize time complexity for large n up to 100000.",
            "Optimize memory usage and avoid unnecessary copies.",
            "Handle edge cases: empty input, duplicates, and invalid order.",
            "Return deterministic output format.",
        ],
        "requirements": {
            "functional": [
                "Implement a function named `solution`.",
                "Pass both visible and hidden testcases.",
                "Return exact expected output format.",
            ],
            "non_functional": [
                "Target <= 2 seconds execution for standard input sizes.",
                "Prefer O(n) or O(n log n) approach where feasible.",
            ],
        },
        "diagram_tools": [],
        "answer_key": {
            "approach": (
                "Identify brute-force baseline, derive optimal data structure strategy, "
                "and validate with edge-case walkthrough."
            ),
            "patterns": [tag for tag in (problem.tags or []) if isinstance(tag, str)],
            "complexity_target": "Time: O(n) to O(n log n), Space: O(1) to O(n)",
        },
        "examples": examples,
    }


@app.get("/api/problems/{problem_id}/details")
async def get_problem_details(problem_id: int, db: Session = Depends(get_db)):
    """Get rich details including examples, constraints, language support, and answer-key guidance."""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    testcases = db.query(TestCase).filter(
        TestCase.problem_id == problem_id,
        TestCase.is_hidden.is_(False),
    ).order_by(TestCase.id.asc()).all()
    return _build_problem_details(problem, testcases)


@app.get("/api/problems/{problem_id}/testcases", response_model=list[TestCaseResponse])
async def list_problem_testcases(
    problem_id: int,
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """List visible testcases for a problem, optionally including hidden cases."""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    query = db.query(TestCase).filter(TestCase.problem_id == problem_id)
    if not include_hidden:
        query = query.filter(TestCase.is_hidden.is_(False))
    testcases = query.order_by(TestCase.id.asc()).all()
    return testcases

@app.get("/problems", response_model=list[ProblemResponse])
async def list_problems(db: Session = Depends(get_db)):
    """List all problems"""
    problems = db.query(Problem).order_by(Problem.id.asc()).all()
    return problems


@app.get("/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: int, db: Session = Depends(get_db)):
    """Get a specific problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    return problem


@app.post("/problems", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem: ProblemCreate,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Create a new problem"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    db_problem = Problem(
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        tags=problem.tags,
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)

    if problem.test_cases:
        testcases = [
            TestCase(
                problem_id=db_problem.id,
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
                is_hidden=test_case.is_hidden,
            )
            for test_case in problem.test_cases
        ]
        db.add_all(testcases)
        db.commit()

    logger.info(f"Problem created: {db_problem.id}")
    return db_problem


@app.put("/problems/{problem_id}", response_model=ProblemResponse)
async def update_problem(
    problem_id: int,
    problem_update: ProblemUpdate,
    db: Session = Depends(get_db)
):
    """Update a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    # Update fields
    if problem_update.title:
        problem.title = problem_update.title
    if problem_update.description:
        problem.description = problem_update.description
    if problem_update.difficulty:
        problem.difficulty = problem_update.difficulty
    if problem_update.tags is not None:
        problem.tags = problem_update.tags

    db.commit()
    db.refresh(problem)

    logger.info(f"Problem updated: {problem_id}")
    return problem


@app.delete("/problems/{problem_id}")
async def delete_problem(problem_id: int, db: Session = Depends(get_db)):
    """Delete a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    db.delete(problem)
    db.commit()

    return {"message": "Problem deleted successfully", "problem_id": problem_id}


@app.post("/problems/{problem_id}/testcases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_problem_testcase(
    problem_id: int,
    testcase: TestCaseCreate,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db),
):
    """Create a testcase for a problem."""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    db_testcase = TestCase(
        problem_id=problem_id,
        input_data=testcase.input_data,
        expected_output=testcase.expected_output,
        is_hidden=testcase.is_hidden,
    )
    db.add(db_testcase)
    db.commit()
    db.refresh(db_testcase)
    return db_testcase


@app.get("/problems/{problem_id}/discussions", response_model=list[DiscussionResponse])
async def list_problem_discussions(problem_id: int, db: Session = Depends(get_db)):
    """List discussion comments for a problem."""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    discussions = db.query(Discussion).filter(
        Discussion.problem_id == problem_id
    ).order_by(Discussion.created_at.desc()).all()

    result: list[DiscussionResponse] = []
    for discussion in discussions:
        user = db.query(User).filter(User.id == discussion.user_id).first()
        result.append(
            DiscussionResponse(
                id=discussion.id,
                problem_id=discussion.problem_id,
                user_id=discussion.user_id,
                username=user.username if user else f"user-{discussion.user_id}",
                content=discussion.content,
                created_at=discussion.created_at,
            )
        )
    return result


@app.post("/problems/{problem_id}/discussions", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED)
async def create_problem_discussion(
    problem_id: int,
    payload: DiscussionCreate,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db),
):
    """Create a discussion comment on a problem."""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    if not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discussion content cannot be empty"
        )

    discussion = Discussion(
        problem_id=problem_id,
        user_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)

    return DiscussionResponse(
        id=discussion.id,
        problem_id=discussion.problem_id,
        user_id=discussion.user_id,
        username=current_user.username,
        content=discussion.content,
        created_at=discussion.created_at,
    )


# ==================== Submissions ====================

@app.post("/problems/{problem_id}/submit", response_model=SubmissionResponse)
async def submit_solution(
    problem_id: int,
    submission: SubmissionCreate,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Submit a solution to a problem"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    # Check if code is valid
    if not submission.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code cannot be empty"
        )

    db_submission = Submission(
        user_id=current_user.id,
        problem_id=problem_id,
        code=submission.code,
        status="queued",
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    execute_submission.delay(db_submission.id)

    logger.info(
        f"Submission created: {db_submission.id} "
        f"by {current_user.username} for problem {problem_id} "
        f"with status queued"
    )
    return db_submission


@app.get("/submissions", response_model=list[SubmissionResponse])
async def list_submissions(
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """List all submissions by current user"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).all()
    return submissions


@app.get("/submissions/{submission_id}", response_model=SubmissionWithProblem)
async def get_submission(
    submission_id: int,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Get a specific submission"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own submissions"
        )

    return submission


@app.get("/problems/{problem_id}/submissions", response_model=list[SubmissionResponse])
async def list_problem_submissions(
    problem_id: int,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """List all submissions for a problem by current user"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    submissions = db.query(Submission).filter(
        Submission.problem_id == problem_id,
        Submission.user_id == current_user.id
    ).all()
    return submissions


# ==================== Statistics ====================
@app.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(db: Session = Depends(get_db)):
    """Return global leaderboard ranked by solved problems and success rate."""
    users = db.query(User).all()
    entries: list[LeaderboardEntry] = []

    for user in users:
        total_submissions = db.query(Submission).filter(
            Submission.user_id == user.id
        ).count()
        accepted_submissions = db.query(Submission).filter(
            Submission.user_id == user.id,
            or_(Submission.status == "accepted", Submission.status == "passed")
        ).count()
        solved_problems = db.query(Submission).filter(
            Submission.user_id == user.id,
            or_(Submission.status == "accepted", Submission.status == "passed")
        ).distinct(Submission.problem_id).count()

        success_rate = (
            (accepted_submissions / total_submissions) * 100
            if total_submissions > 0 else 0.0
        )

        entries.append(
            LeaderboardEntry(
                user_id=user.id,
                username=user.username,
                solved_problems=solved_problems,
                total_submissions=total_submissions,
                accepted_submissions=accepted_submissions,
                success_rate=success_rate,
            )
        )

    entries.sort(
        key=lambda entry: (
            entry.solved_problems,
            entry.success_rate,
            entry.accepted_submissions,
        ),
        reverse=True,
    )
    return entries


@app.get("/stats")
async def get_stats(
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Get user statistics"""
    current_user = db.query(User).filter(User.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    total_submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).count()

    passed_submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id,
        or_(Submission.status == "accepted", Submission.status == "passed")
    ).count()

    unique_problems_solved = db.query(Submission).filter(
        Submission.user_id == current_user.id,
        or_(Submission.status == "accepted", Submission.status == "passed")
    ).distinct(Submission.problem_id).count()

    return {
        "total_submissions": total_submissions,
        "passed_submissions": passed_submissions,
        "unique_problems_solved": unique_problems_solved,
        "success_rate": (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
