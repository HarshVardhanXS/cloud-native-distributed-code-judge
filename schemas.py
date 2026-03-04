from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
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
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"
    tags: Optional[list[str]] = None


class ProblemCreate(ProblemBase):
    test_cases: Optional[list["TestCaseCreate"]] = None


class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Literal["Easy", "Medium", "Hard"]] = None
    tags: Optional[list[str]] = None


class ProblemResponse(ProblemBase):
    id: int
    created_at: datetime

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


class TestCaseBase(BaseModel):
    input_data: str
    expected_output: str
    is_hidden: bool = True


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseResponse(TestCaseBase):
    id: int
    problem_id: int

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    user_id: int
    username: str
    solved_problems: int
    total_submissions: int
    accepted_submissions: int
    success_rate: float


class DiscussionCreate(BaseModel):
    content: str


class DiscussionResponse(BaseModel):
    id: int
    problem_id: int
    user_id: int
    username: str
    content: str
    created_at: datetime
