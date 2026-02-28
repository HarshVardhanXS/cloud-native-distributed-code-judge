from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class ProblemBase(BaseModel):
    title: str
    description: str
    difficulty: str = "medium"
    test_cases: str  # JSON string


class ProblemCreate(ProblemBase):
    pass


class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    test_cases: Optional[str] = None


class ProblemResponse(ProblemBase):
    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubmissionBase(BaseModel):
    code: str


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionResponse(SubmissionBase):
    id: int
    user_id: int
    problem_id: int
    status: str
    result: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionWithProblem(SubmissionResponse):
    problem: ProblemResponse
