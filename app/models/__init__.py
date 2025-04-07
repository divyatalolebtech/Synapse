from enum import Enum
from .base import Base, engine, get_db
from .assessment import AssessmentSession, Question, UserResponse
from .learning_resource import LearningResource

class Role(str, Enum):
    software_engineer = 'software_engineer'
    data_scientist = 'data_scientist'
    devops_engineer = 'devops_engineer'

class SkillDimension(str, Enum):
    algorithm_knowledge = 'algorithm_knowledge'
    coding_proficiency = 'coding_proficiency'
    system_design = 'system_design'
    database_management = 'database_management'
    testing_qa = 'testing_qa'
    devops_knowledge = 'devops_knowledge'
    cloud_services = 'cloud_services'
    communication = 'communication'
    data_analysis = 'data_analysis'
    machine_learning = 'machine_learning'

__all__ = [
    'Base', 'engine', 'get_db',
    'AssessmentSession', 'Question', 'UserResponse',
    'LearningResource',
    'Role', 'SkillDimension'
]
