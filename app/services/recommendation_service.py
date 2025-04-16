from typing import List, Dict
import logging
from sqlalchemy.orm import Session
from app.models.learning_resource import LearningResource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        # Initialize skill keywords mapping to our assessment dimensions
        self.skill_keywords = {
            "algorithm_knowledge": ["algorithms", "data structures", "complexity", "problem solving"],
            "coding_proficiency": ["programming", "coding", "software development", "implementation"],
            "system_design": ["system design", "architecture", "scalability", "distributed systems"],
            "debugging": ["debugging", "troubleshooting", "error handling", "testing"],
            "testing_qa": ["testing", "quality assurance", "test automation", "unit testing"],
            "devops": ["devops", "ci/cd", "deployment", "infrastructure", "cloud"],
            "security": ["security", "authentication", "authorization", "encryption"],
            "communication": ["documentation", "technical writing", "collaboration", "teamwork"]
        }
        
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using keyword matching"""
        text = text.lower()
        detected_skills = []
        
        for skill, keywords in self.skill_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_skills.append(skill)
                
        return detected_skills
        
    def get_recommendations(
        self,
        db: Session,
        weak_skills: List[str],
        limit: int = 6,
        role: str = None
    ) -> List[Dict]:
        """Get course recommendations based on skill matching"""
        try:
            logger.info(f"Starting recommendation process for {len(weak_skills)} weak skills")
            
            if role:
                logger.info(f"Generating recommendations for role: {role}")
                
            if not weak_skills:
                logger.warning("No weak skills provided, using default skills")
                weak_skills = list(self.skill_keywords.keys())
            
            # Get all resources
            resources = db.query(LearningResource).all()
            logger.info(f"Found {len(resources)} resources")
            
            if not resources:
                logger.warning("No learning resources found in database")
                return []
            
            # Score resources based on skill keyword matches
            scored = []
            for resource in resources:
                score = 0
                description = (resource.description or "").lower()
                title = (resource.title or "").lower()
                
                # Check for skill keyword matches
                for skill in weak_skills:
                    keywords = self.skill_keywords.get(skill, [])
                    for keyword in keywords:
                        if keyword in description or keyword in title:
                            score += 1
                
                if score > 0:
                    scored.append((score, resource))
            
            # Sort by match score (highest first)
            scored.sort(key=lambda x: x[0], reverse=True)
            
            # Return top N with relevance scores
            recommendations = [
                {
                    **resource.to_dict(),
                    "relevance_score": round((score / len(weak_skills)) * 100, 2)
                }
                for score, resource in scored[:limit]
            ]
            
            logger.info(f"Returning top {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation process failed: {e}")
            raise
