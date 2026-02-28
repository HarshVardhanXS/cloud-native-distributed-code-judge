from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from datetime import timedelta
import json
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database import init_db, get_db
from models import User, Problem, Submission
from schemas import (
    UserCreate, UserResponse, Token,
    ProblemCreate, ProblemResponse, ProblemUpdate,
    SubmissionCreate, SubmissionResponse, SubmissionWithProblem
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_username_from_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from judge import execute_code_sync

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    init_db()
    logger.info("Database initialized")
    
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


# ==================== Problems ====================

@app.get("/problems", response_model=list[ProblemResponse])
async def list_problems(db: Session = Depends(get_db)):
    """List all problems"""
    problems = db.query(Problem).all()
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


@app.post("/problems", response_model=ProblemResponse)
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
    # Validate test cases JSON
    try:
        json.loads(problem.test_cases)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_cases must be valid JSON"
        )

    db_problem = Problem(
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        test_cases=problem.test_cases,
        creator_id=current_user.id
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)

    logger.info(f"Problem created: {db_problem.id} by {username}")
    return db_problem


@app.put("/problems/{problem_id}", response_model=ProblemResponse)
async def update_problem(
    problem_id: int,
    problem_update: ProblemUpdate,
    username: str = Depends(get_current_username_from_token),
    db: Session = Depends(get_db)
):
    """Update a problem (only by creator)"""
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

    if problem.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator can update this problem"
        )

    # Validate test cases if provided
    if problem_update.test_cases:
        try:
            json.loads(problem_update.test_cases)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="test_cases must be valid JSON"
            )

    # Update fields
    if problem_update.title:
        problem.title = problem_update.title
    if problem_update.description:
        problem.description = problem_update.description
    if problem_update.difficulty:
        problem.difficulty = problem_update.difficulty
    if problem_update.test_cases:
        problem.test_cases = problem_update.test_cases

    db.commit()
    db.refresh(problem)

    logger.info(f"Problem updated: {problem_id}")
    return problem


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

    # Execute code against test cases
    execution_result = execute_code_sync(submission.code, problem.test_cases)

    db_submission = Submission(
        user_id=current_user.id,
        problem_id=problem_id,
        code=submission.code,
        status=execution_result["status"],
        result=json.dumps(execution_result)
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    logger.info(
        f"Submission created: {db_submission.id} "
        f"by {current_user.username} for problem {problem_id} "
        f"with status {execution_result['status']}"
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
        Submission.status == "passed"
    ).count()

    unique_problems_solved = db.query(Submission).filter(
        Submission.user_id == current_user.id,
        Submission.status == "passed"
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
