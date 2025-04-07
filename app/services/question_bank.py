from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
from app.models.assessment import Question

class QuestionBankManager:
    def __init__(self, db: Session):
        self.db = db

    def add_question(self, question_data: Dict) -> Question:
        """Add a new question to the question bank."""
        question = Question(
            text=question_data["text"],
            options=json.dumps(question_data["options"]),
            correct_answer=question_data["correct_answer"],
            difficulty=question_data["difficulty"],
            role=question_data["role"],
            skill_dimension=question_data["skill_dimension"]
        )
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def get_questions_by_role(self, role: str) -> List[Question]:
        """Get all questions for a specific role."""
        return self.db.query(Question).filter(Question.role == role).all()

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """Get a specific question by its ID."""
        return self.db.query(Question).filter(Question.id == question_id).first()

    def get_questions_by_skill(self, role: str, skill_dimension: str) -> List[Question]:
        """Get all questions for a specific role and skill dimension."""
        return self.db.query(Question).filter(
            Question.role == role,
            Question.skill_dimension == skill_dimension
        ).all()

    def get_questions_by_difficulty(self, role: str, difficulty: int) -> List[Question]:
        """Get all questions for a specific role and difficulty level."""
        return self.db.query(Question).filter(
            Question.role == role,
            Question.difficulty == difficulty
        ).all()

    def update_question(self, question_id: int, updates: dict) -> Optional[Question]:
        """Update an existing question."""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if question:
            for key, value in updates.items():
                setattr(question, key, value)
            self.db.commit()
            self.db.refresh(question)
        return question

    def delete_question(self, question_id: int) -> bool:
        """Delete a question from the question bank."""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if question:
            self.db.delete(question)
            self.db.commit()
            return True
        return False

    def get_question_count(self, role: str) -> int:
        """Get total number of questions for a role."""
        return self.db.query(Question).filter(Question.role == role).count()

    def get_skill_coverage(self, role: str) -> dict:
        """Get the distribution of questions across skill dimensions."""
        coverage = {}
        questions = self.db.query(Question).filter(Question.role == role).all()
        for question in questions:
            skill = question.skill_dimension
            if skill not in coverage:
                coverage[skill] = 0
            coverage[skill] += 1
        return coverage
