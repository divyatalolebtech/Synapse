from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class StartAssessment(BaseModel):
    role: str

class DimensionScore(BaseModel):
    dimension: str
    score: float
    level: str

class Progress(BaseModel):
    completed: int
    total: int
    percentage: float
    skill_scores: Optional[List[DimensionScore]] = None

class Question(BaseModel):
    id: int
    text: str
    options: Dict[str, str]
    difficulty: int
    role: str
    skill_dimension: str
    progress: Optional[Progress] = None

class AssessmentSession(BaseModel):
    id: str
    role: str
    current_question: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

class SubmitResponse(BaseModel):
    question_id: int
    response: str

class Response(BaseModel):
    session_id: str
    question_id: int
    response: str
    is_correct: bool
    timestamp: datetime
    next_question_available: bool = True

class AssessmentResult(BaseModel):
    session_id: str
    role: str
    overall_score: float
    dimension_scores: List[DimensionScore]
    end_time: datetime
    status: str
