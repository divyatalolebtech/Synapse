from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import random
import logging
from app.models.assessment import Question as QuestionModel, UserResponse, AssessmentSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveEngine:
    def __init__(self, db: Session):
        self.db = db
        
    def initialize_difficulty_map(self) -> Dict[str, float]:
        """Initialize difficulty estimates for each skill dimension."""
        # Get all unique skill dimensions from the question bank
        skill_dimensions = self.db.query(QuestionModel.skill_dimension).distinct().all()
        skill_dimensions = [s[0] for s in skill_dimensions]  # Extract string values
        
        # Start with medium difficulty (3) for all skills
        return {skill: 3.0 for skill in skill_dimensions}
        
    def update_difficulty_estimates(
        self,
        session_id: str,
        current_estimates: Dict[str, float]
    ) -> Dict[str, float]:
        """Update difficulty estimates based on user performance."""
        responses = self.db.query(UserResponse).filter(
            UserResponse.session_id == session_id
        ).all()
        
        if not responses:
            return current_estimates
            
        skill_correct_count = {}
        skill_total_count = {}
        
        for response in responses:
            question = self.db.query(QuestionModel).filter(QuestionModel.id == response.question_id).first()
            if question:
                skill = question.skill_dimension
                if skill not in skill_correct_count:
                    skill_correct_count[skill] = 0
                    skill_total_count[skill] = 0
                    
                skill_total_count[skill] += 1
                if response.is_correct:
                    skill_correct_count[skill] += 1
                    
        # Update estimates based on performance
        new_estimates = current_estimates.copy()
        for skill in current_estimates:
            if skill in skill_total_count and skill_total_count[skill] > 0:
                success_rate = skill_correct_count[skill] / skill_total_count[skill]
                if success_rate > 0.7:  # Too easy
                    new_estimates[skill] = min(5, current_estimates[skill] + 0.5)
                elif success_rate < 0.3:  # Too hard
                    new_estimates[skill] = max(1, current_estimates[skill] - 0.5)
                    
        return new_estimates
        
    def select_next_question(
        self,
        role: str,
        answered_ids: List[int],
        skill_scores: Dict[str, float]
    ) -> Optional[QuestionModel]:
        """Select the next question based on adaptive algorithm."""
        try:
            logger.info(f"Selecting next question for role: {role}")
            logger.info(f"Already answered questions: {len(answered_ids)}")
            logger.info(f"Current skill scores: {skill_scores}")
            
            # Get all available questions for this role that haven't been answered
            all_questions = self.db.query(QuestionModel).filter(
                QuestionModel.role == role,
                ~QuestionModel.id.in_(answered_ids)
            ).all()
            logger.info(f"Found {len(all_questions)} available questions")
            
            if not all_questions:
                logger.warning("No more questions available for this role")
                return None
            
            # Stop after 40 questions
            if len(answered_ids) >= 40:
                logger.info("Reached maximum questions (40)")
                return None
            
            # Find skills with lowest scores
            if skill_scores:
                target_skill = min(skill_scores.items(), key=lambda x: x[1])[0]
                logger.info(f"Selected target skill {target_skill} based on lowest score: {skill_scores[target_skill]}")
            else:
                # If no scores yet, pick a random skill from available questions
                available_skills = {q.skill_dimension for q in all_questions}
                target_skill = random.choice(list(available_skills))
                logger.info(f"No skill scores yet, randomly selected target skill: {target_skill}")
            
            # Get questions for target skill
            available_questions = [q for q in all_questions if q.skill_dimension == target_skill]
            logger.info(f"Found {len(available_questions)} questions for target skill {target_skill}")
            
            if not available_questions:
                # If no questions for target skill, return any available question
                logger.warning(f"No questions available for target skill {target_skill}, selecting random question")
                return random.choice(all_questions)
            
            # Get current difficulty for target skill or default to medium (3)
            target_difficulty = 3.0
            if skill_scores:
                # Adjust difficulty based on score
                score = skill_scores[target_skill]
                if score < 30:
                    target_difficulty = 2.0  # Easier
                    logger.info(f"Score {score} < 30%, selecting easier questions (difficulty {target_difficulty})")
                elif score > 70:
                    target_difficulty = 4.0  # Harder
                    logger.info(f"Score {score} > 70%, selecting harder questions (difficulty {target_difficulty})")
                else:
                    logger.info(f"Score {score} between 30-70%, keeping medium difficulty {target_difficulty}")
            
            # Select question closest to target difficulty
            selected_question = min(
                available_questions,
                key=lambda q: abs(q.difficulty - target_difficulty)
            )
            
            logger.info(f"Selected question {selected_question.id} with difficulty {selected_question.difficulty}")
            return selected_question
            
        except Exception as e:
            logger.error(f"Error in select_next_question: {str(e)}")
            return None
