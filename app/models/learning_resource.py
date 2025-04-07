from sqlalchemy import Column, Integer, String, Float, JSON, PickleType
from .base import Base

class LearningResource(Base):
    __tablename__ = "learning_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    platform = Column(String)
    skills = Column(JSON)  # List of skills as JSON array
    url = Column(String)
    cost = Column(Float)
    duration_hours = Column(Float)
    embedding = Column(PickleType, nullable=True)  # Store sentence embeddings
    relevance_score = Column(Float, default=0.0)  # Store relevance score

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "platform": self.platform,
            "skills": self.skills,
            "url": self.url,
            "cost": self.cost,
            "duration_hours": self.duration_hours,
            "embedding": self.embedding,
            "relevance_score": self.relevance_score
        }
