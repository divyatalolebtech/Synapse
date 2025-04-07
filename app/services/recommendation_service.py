from typing import List, Dict
import numpy as np
import logging
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.learning_resource import LearningResource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
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
        role: str = None  # Add role parameter to prevent error
    ) -> List[Dict]:
        """Get course recommendations based on semantic similarity"""
        try:
            logger.info(f"Starting recommendation process for {len(weak_skills)} weak skills")
            logger.debug(f"Weak skills: {weak_skills}")
            
            if role:
                logger.info(f"Generating recommendations for role: {role}")
                
            if not weak_skills:
                logger.warning("No weak skills provided, recommendations may be less relevant")
                weak_skills = ["general programming"]  # Fallback
            
            # Join weak skills into a single text query
            query_text = " ".join(weak_skills)
            logger.debug(f"Generated query text: {query_text}")
            
            # Generate query embedding
            try:
                query_embedding = self.model.encode(query_text).reshape(1, -1)
                logger.info(f"Generated query embedding of shape {query_embedding.shape}")
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                raise

            # Get all resources with embeddings
            try:
                resources = db.query(LearningResource).filter(LearningResource.embedding != None).all()
                logger.info(f"Found {len(resources)} resources with embeddings")
                
                if not resources:
                    logger.warning("No learning resources found in database")
                    return []
                    
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                raise
            
            # Score each resource using cosine similarity
            scored = []
            error_count = 0
            
            for resource in resources:
                if not resource.embedding:
                    continue
                    
                try:
                    resource_embedding = np.array(resource.embedding).reshape(1, -1)
                    score = cosine_similarity(query_embedding, resource_embedding)[0][0]
                    scored.append((score, resource))
                    logger.debug(f"Scored '{resource.title}': {score:.4f}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to score resource '{resource.title}': {e}")
                    continue

            if error_count:
                logger.warning(f"Failed to score {error_count} resources")

            # Sort by similarity score (highest first)
            scored.sort(key=lambda x: x[0], reverse=True)
            logger.info(f"Sorted {len(scored)} resources by relevance score")
            
            # Return top N with relevance scores
            recommendations = [
                {
                    **resource.to_dict(),
                    "relevance_score": round(score * 100, 2)
                }
                for score, resource in scored[:limit]
            ]
            
            logger.info(f"Returning top {len(recommendations)} recommendations")
            logger.debug("Recommendations: %s", 
                        [(r['title'], r['relevance_score']) for r in recommendations])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation process failed: {e}")
            raise
