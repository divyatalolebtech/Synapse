import json
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from app.models.learning_resource import LearningResource
from app.services.recommendation_service import RecommendationService

def load_courses_from_json(path: str = None) -> List[Dict[str, Any]]:
    """Load courses from a JSON file or fallback to sample courses."""
    if path is None:
        path = Path(__file__).parent.parent / "data" / "real_courses.json"
    else:
        path = Path(path)
        
    if not path.exists():
        # Fallback to sample courses if real courses don't exist
        from app.data.sample_courses import SAMPLE_COURSES
        print("Real courses not found, using sample courses")
        return SAMPLE_COURSES
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            courses = json.load(f)
            print(f"Loaded {len(courses)} courses from {path}")
            return courses
    except Exception as e:
        print(f"Error loading courses from {path}: {e}")
        from app.data.sample_courses import SAMPLE_COURSES
        return SAMPLE_COURSES

class CourseIngestionService:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.recommendation_service = RecommendationService()
        self.model = SentenceTransformer(model_name)
    
    def process_course(self, course: dict) -> dict:
        """Process a single course by adding embeddings and extracted skills"""
        try:
            # Extract additional skills from description
            extracted_skills = self.recommendation_service.extract_skills(
                course["description"]
            )
            
            # Combine predefined and extracted skills
            all_skills = list(set(course["skills"] + extracted_skills))
            
            # Generate embedding for the course
            text_to_embed = course["title"] + " " + course["description"]
            embedding = self.model.encode(text_to_embed).tolist()
            
            # Return course with embeddings, updated skills, and default relevance score
            return {
                **course,
                "skills": all_skills,
                "embedding": embedding,
                "relevance_score": course.get('relevance_score', 0.0)  # Default to 0.0 if not provided
            }
            
        except Exception as e:
            print(f"Error processing course {course['title']}: {str(e)}")
            raise
    
    def ingest_courses(self, db: Session, courses_data=None):
        """Ingest courses into the database.
        
        Args:
            db (Session): Database session
            courses_data: Either a list of course dictionaries or a path to JSON file
        """
        try:
            print("Checking for existing courses...")
            # Delete existing courses to force re-ingestion
            db.query(LearningResource).delete()
            db.commit()
            print("Deleted existing courses")
            
            # Handle both direct course data and file paths
            if isinstance(courses_data, list):
                courses = courses_data
                print(f"Using provided course data: {len(courses)} courses")
            else:
                courses = load_courses_from_json(courses_data)
                print(f"Loaded {len(courses)} courses from file")
            
            for course in courses:
                course_with_embedding = self.process_course(course)
                resource = LearningResource(**course_with_embedding)
                db.add(resource)
                print(f"Added course: {course['title']}")
            
            db.commit()
            final_count = db.query(LearningResource).count()
            print(f"Course ingestion complete. Total courses: {final_count}")
            
        except Exception as e:
            print(f"Error during course ingestion: {str(e)}")
            db.rollback()
            raise
