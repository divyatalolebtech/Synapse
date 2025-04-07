from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from app.models.base import Base, engine, get_db
from app.models.assessment import Question as QuestionModel, AssessmentSession as AssessmentSessionModel, UserResponse
from app.schemas.assessment import (
    StartAssessment,
    Question as QuestionSchema,
    AssessmentSession as AssessmentSessionSchema,
    SubmitResponse,
    Response,
    AssessmentResult,
    DimensionScore,
    Progress
)
from app.services.question_bank import QuestionBankManager
from app.services.adaptive_engine import AdaptiveEngine
from app.data.sample_questions import get_questions_for_role, ROLES, SKILL_DIMENSIONS
from app.services.course_ingestion_service import CourseIngestionService
from app.data.fetch_real_courses import fetch_coursera_courses
from app.routers import recommendations
import uuid
from datetime import datetime
import os
import json

# Define skill dimensions
skill_dimensions = list(SKILL_DIMENSIONS.values())

# Drop and recreate all tables
print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Database tables recreated successfully")

app = FastAPI(title="Tech Industry Competency Assessment Engine")

# Get absolute paths
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(app_dir, "app", "templates")
static_dir = os.path.join(app_dir, "app", "static")

print(f"App dir: {app_dir}")
print(f"Templates dir: {templates_dir}")
print(f"Static dir: {static_dir}")

# Setup templates
templates = Jinja2Templates(directory=templates_dir)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize question bank with sample questions
def init_question_bank(db: Session):
    qb = QuestionBankManager(db)
    
    # First, check if we already have questions
    existing_count = db.query(QuestionModel).count()
    if existing_count > 0:
        print(f"Found {existing_count} existing questions, skipping initialization")
        return
    
    print("Starting question bank initialization...")
    # Add questions for each role
    for role in ROLES.values():
        questions = get_questions_for_role(role)
        for question in questions:
            try:
                # Add role to the question dict
                question_with_role = question.copy()
                question_with_role['role'] = role
                qb.add_question(question_with_role)
                print(f"Added question for {role}: {question['text'][:50]}...")
            except Exception as e:
                print(f"Error adding question: {e}")
    
    final_count = db.query(QuestionModel).count()
    print(f"Question bank initialization complete. Total questions: {final_count}")

@app.on_event("startup")
async def startup_event():
    """Initialize question bank and course data on startup."""
    db = next(get_db())
    try:
        # Initialize question bank
        init_question_bank(db)
        print("Question bank initialized successfully")
        
        # Fetch and ingest real courses from Coursera
        print("Fetching courses from Coursera...")
        courses = fetch_coursera_courses()
        if courses:
            print(f"Fetched {len(courses)} courses from Coursera")
            course_service = CourseIngestionService()
            course_service.ingest_courses(db, courses)
            print("Course data initialized successfully")
        else:
            print("Warning: No courses fetched from Coursera, check API response")
    except Exception as e:
        print(f"Error during initialization: {e}")
    finally:
        db.close()

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/assessment/{assessment_id}")
async def assessment_page(request: Request, assessment_id: str):
    return templates.TemplateResponse("assessment.html", {"request": request})

@app.get("/results/{session_id}")
async def results_page(request: Request, session_id: str):
    """Serve the results page HTML."""
    return templates.TemplateResponse("results.html", {"request": request, "session_id": session_id})

@app.get("/recommendations/{session_id}")
async def recommendation_page(request: Request, session_id: str):
    """Serve the recommendations page HTML."""
    return templates.TemplateResponse("recommendations.html", {"request": request, "session_id": session_id})

@app.get("/api/results/{session_id}", response_model=AssessmentResult)
async def get_results(session_id: str, db: Session = Depends(get_db)):
    """Get the assessment results as JSON."""
    try:
        session = db.query(AssessmentSessionModel).filter(
            AssessmentSessionModel.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Assessment not completed")
            
        # Get all responses for this session
        responses = db.query(UserResponse).filter(
            UserResponse.session_id == session_id
        ).all()
        
        # Get all skill dimensions for this role
        skill_dimensions = db.query(QuestionModel.skill_dimension).distinct().filter(
            QuestionModel.role == session.role
        ).all()
        skill_dimensions = [dim[0] for dim in skill_dimensions]
        
        # Calculate overall score and dimension scores
        total_questions = len(responses)
        correct_answers = sum(1 for r in responses if r.is_correct)
        overall_score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        dimension_scores = []
        for skill in skill_dimensions:
            # Get questions for this skill dimension
            skill_questions = db.query(QuestionModel).join(
                UserResponse,
                QuestionModel.id == UserResponse.question_id
            ).filter(
                UserResponse.session_id == session_id,
                QuestionModel.skill_dimension == skill
            ).all()
            
            if skill_questions:
                correct = sum(1 for q in skill_questions if db.query(UserResponse).filter(
                    UserResponse.question_id == q.id,
                    UserResponse.session_id == session_id,
                    UserResponse.is_correct == True
                ).first())
                
                score = (correct / len(skill_questions)) * 100
            else:
                score = 0
            
            dimension_scores.append(DimensionScore(
                dimension=skill,
                score=score,
                level=get_competency_level(score)
            ))
        
        return AssessmentResult(
            session_id=session_id,
            role=session.role,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            end_time=session.end_time,
            status=session.status
        )
        
    except Exception as e:
        print(f"Error in get_results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/assessments/start", response_model=AssessmentSessionSchema)
async def start_assessment(request: StartAssessment, db: Session = Depends(get_db)):
    """Start a new assessment for a given role."""
    try:
        session_id = str(uuid.uuid4())
        session = AssessmentSessionModel(
            id=session_id,
            role=request.role,
            current_question=0,
            status="in_progress",
            start_time=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        return session
    except Exception as e:
        print(f"Error in start_assessment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/questions/{session_id}", response_model=QuestionSchema)
async def get_next_question(session_id: str, db: Session = Depends(get_db)):
    """Get the next question for the assessment session using adaptive selection."""
    try:
        session = db.query(AssessmentSessionModel).filter(
            AssessmentSessionModel.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Assessment already completed")
        
        # Get answered questions
        answered_questions = db.query(UserResponse.question_id).filter(
            UserResponse.session_id == session_id
        ).all()
        answered_ids = [q[0] for q in answered_questions]
        
        # Get total questions for this role
        total_questions = db.query(QuestionModel).filter(
            QuestionModel.role == session.role
        ).count()
        
        # Calculate progress
        progress_percentage = (len(answered_ids) / 40) * 100 if answered_ids else 0
        
        # Get skill dimensions covered so far
        skill_dimensions = db.query(QuestionModel.skill_dimension).distinct().filter(
            QuestionModel.role == session.role
        ).all()
        skill_dimensions = [dim[0] for dim in skill_dimensions]
        
        # Initialize skill scores with 0%
        skill_scores = {skill: 0 for skill in skill_dimensions}
        
        # Calculate skill scores for answered questions
        if answered_ids:
            for skill in skill_dimensions:
                skill_questions = db.query(UserResponse).join(
                    QuestionModel,
                    UserResponse.question_id == QuestionModel.id
                ).filter(
                    UserResponse.session_id == session_id,
                    QuestionModel.skill_dimension == skill
                ).all()
                
                if skill_questions:
                    correct = sum(1 for q in skill_questions if q.is_correct)
                    total = len(skill_questions)
                    skill_scores[skill] = min((correct / total) * 100, 100)  # Ensure score doesn't exceed 100%
        
        # Create dimension scores for progress tracking
        dimension_scores = [
            DimensionScore(
                dimension=skill,
                score=score,
                level=get_competency_level(score)
            )
            for skill, score in skill_scores.items()
        ]
        
        # Get next question using adaptive engine
        adaptive_engine = AdaptiveEngine(db)
        next_question = adaptive_engine.select_next_question(
            session.role,
            answered_ids,
            skill_scores
        )
        
        if not next_question:
            session.status = "completed"
            session.end_time = datetime.utcnow()
            db.commit()
            raise HTTPException(
                status_code=404,
                detail="No more questions available"
            )
        
        # Add progress information
        # Parse options from JSON string to dict
        try:
            options_dict = json.loads(next_question.options)
        except json.JSONDecodeError as e:
            print(f"Error parsing options JSON: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error parsing question options: {str(e)}"
            )
            
        return QuestionSchema(
            id=next_question.id,
            text=next_question.text,
            options=options_dict,
            difficulty=next_question.difficulty,
            role=next_question.role,
            skill_dimension=next_question.skill_dimension,
            progress=Progress(
                completed=len(answered_ids),
                total=40,
                percentage=progress_percentage,
                skill_scores=dimension_scores
            )
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions without wrapping
        raise e
    except Exception as e:
        print(f"Error in get_next_question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/responses/{session_id}", response_model=Response)
async def submit_response(
    session_id: str,
    response: SubmitResponse,
    db: Session = Depends(get_db)
):
    """Submit a response for a question."""
    try:
        session = db.query(AssessmentSessionModel).filter(
            AssessmentSessionModel.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Assessment already completed")
        
        question = db.query(QuestionModel).filter(
            QuestionModel.id == response.question_id
        ).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check if the response matches the correct answer
        is_correct = response.response == question.correct_answer
        
        user_response = UserResponse(
            session_id=session_id,
            question_id=response.question_id,
            response=response.response,
            is_correct=is_correct,
            timestamp=datetime.utcnow()
        )
        
        db.add(user_response)
        db.commit()
        
        # Calculate progress
        total_questions = 40  # Fixed at 40 questions for all roles
        answered_questions = db.query(UserResponse).filter(
            UserResponse.session_id == session_id
        ).count()
        
        # End test after 40 questions
        if answered_questions >= total_questions:
            # Update session status and end time
            session.status = "completed"
            session.end_time = datetime.utcnow()
            db.commit()
            
            # Return response with next_question_available=False
            next_question_available = False
        else:
            next_question_available = True
        
        # Create response object
        response_obj = Response(
            session_id=session_id,
            question_id=response.question_id,
            response=response.response,
            is_correct=is_correct,
            timestamp=datetime.utcnow(),
            next_question_available=next_question_available
        )
        
        # If this is the last response and session is completed, update end_time and status
        if not next_question_available:
            session.end_time = datetime.utcnow()
            session.status = "completed"
            db.commit()
            
        return response_obj
        
    except Exception as e:
        print(f"Error in submit_response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

def get_competency_level(score: float) -> str:
    """Convert numerical score to competency level."""
    if score <= 20:
        return "Beginner"
    elif score <= 40:
        return "Foundational"
    elif score <= 60:
        return "Intermediate"
    elif score <= 80:
        return "Advanced"
    else:
        return "Expert"

# Admin endpoint to manually trigger course ingestion
@app.post("/admin/ingest-courses")
async def ingest_courses(db: Session = Depends(get_db)):
    """Manually trigger course ingestion from real_courses.json"""
    try:
        course_service = CourseIngestionService()
        course_service.ingest_courses(db)
        return {"status": "success", "message": "Courses ingested successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting courses: {str(e)}"
        )

# Include recommendation router
app.include_router(recommendations.router)
