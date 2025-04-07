import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.base import get_db
from app.models.assessment import Question as QuestionModel, AssessmentSession, UserResponse
from app.models.learning_resource import LearningResource
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendations import CourseRecommendation, RecommendationResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
recommendation_service = RecommendationService()

@router.get("/api/recommendations/{session_id}", response_model=RecommendationResponse)
async def get_recommendations(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get personalized course recommendations based on assessment results"""
    logger.info(f"Processing recommendations for session: {session_id}")
    
    # Step 1: Validate session exists and is completed
    try:
        session = db.query(AssessmentSession).filter(
            AssessmentSession.id == session_id
        ).first()
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Session not found",
                    "code": "SESSION_NOT_FOUND"
                }
            )
            
        if session.status != "completed":
            logger.warning(f"Incomplete assessment for session: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Assessment must be completed before viewing recommendations",
                    "code": "ASSESSMENT_INCOMPLETE"
                }
            )
        
        logger.info(f"Found valid session {session_id} with status: {session.status}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error validating assessment session",
                "code": "SESSION_VALIDATION_ERROR"
            }
        )
    
    # Step 2: Get user responses and calculate skill scores
    try:
        responses = db.query(UserResponse).filter(
            UserResponse.session_id == session_id
        ).all()
        
        if not responses:
            logger.warning(f"No responses found for session: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No assessment responses found",
                    "code": "NO_RESPONSES"
                }
            )
            
        logger.info(f"Found {len(responses)} responses for session {session_id}")
        
        # Calculate skill scores
        skill_scores = {}
        for response in responses:
            question = db.query(QuestionModel).filter(
                QuestionModel.id == response.question_id
            ).first()
            
            if not question:
                logger.warning(f"Question {response.question_id} not found for response")
                continue
                
            if question.skill_dimension not in skill_scores:
                skill_scores[question.skill_dimension] = {"correct": 0, "total": 0}
            
            skill_scores[question.skill_dimension]["total"] += 1
            if response.is_correct:
                skill_scores[question.skill_dimension]["correct"] += 1
        
        # Identify weak skills (score < 70%)
        weak_skills = [
            skill for skill, scores in skill_scores.items()
            if (scores["correct"] / scores["total"]) < 0.7
        ]
        
        if not weak_skills:
            logger.info("No weak skills identified, using all skill dimensions")
            weak_skills = list(skill_scores.keys())
            
        logger.info(f"Identified weak skills: {weak_skills}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing responses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error processing assessment responses",
                "code": "RESPONSE_PROCESSING_ERROR"
            }
        )
    
    # Step 3: Generate recommendations
    try:
        # Check if we have any courses
        course_count = db.query(LearningResource).count()
        logger.info(f"Found {course_count} total courses in database")
        
        if course_count == 0:
            logger.warning("No courses found in database")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Course recommendations are temporarily unavailable",
                    "code": "NO_COURSES"
                }
            )
        
        # Get recommendations based on role and weak skills
        recommendations = recommendation_service.get_recommendations(
            db=db,
            weak_skills=weak_skills,
            role=session.role,  # Pass the role from the assessment session
            limit=6
        )
        
        if not recommendations:
            logger.warning("No recommendations generated")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No suitable course recommendations found",
                    "code": "NO_RECOMMENDATIONS"
                }
            )
        
        response_data = {
            "session_id": session_id,
            "weak_skills": weak_skills,
            "recommendations": recommendations
        }
        
        logger.info(f"Successfully generated {len(recommendations)} recommendations")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error generating course recommendations",
                "code": "RECOMMENDATION_ERROR"
            }
        )
