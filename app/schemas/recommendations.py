from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CourseRecommendation(BaseModel):
    id: int
    title: str
    description: str
    platform: str
    skills: List[str]
    url: str
    cost: float
    duration_hours: float
    relevance_score: float

class RecommendationResponse(BaseModel):
    session_id: str
    weak_skills: List[str]
    recommendations: List[CourseRecommendation]
    generated_at: datetime = datetime.utcnow()
