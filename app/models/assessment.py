from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id = Column(String, primary_key=True, index=True)
    role = Column(String)
    current_question = Column(Integer, default=0)
    status = Column(String, default="in_progress")  # in_progress, completed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    responses = relationship("UserResponse", back_populates="session")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    options = Column(String)  # JSON string of options
    correct_answer = Column(String)
    difficulty = Column(Integer)
    role = Column(String)
    skill_dimension = Column(String)
    
    responses = relationship("UserResponse", back_populates="question")

class UserResponse(Base):
    __tablename__ = "user_responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("assessment_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    response = Column(String)
    is_correct = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("AssessmentSession", back_populates="responses")
    question = relationship("Question", back_populates="responses")
