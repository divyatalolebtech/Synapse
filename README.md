# Tech Industry Competency Assessment Engine

A sophisticated assessment and learning recommendation system that evaluates technical competencies and suggests personalized Coursera courses based on skill gaps.

## Features

- Support for multiple tech roles (Software Engineer, Data Scientist, DevOps Engineer)
- Adaptive questioning system
- Comprehensive competency scoring across key skill dimensions:
  - Algorithm Knowledge
  - Coding Proficiency
  - System Design
  - Debugging
  - Testing & QA
  - DevOps
  - Security
  - Communication
- Personalized Coursera course recommendations based on assessment results
- Real-time course data integration with Coursera's API
- Smart skill mapping and course relevance scoring

## Technical Stack

- Backend: FastAPI + Python
- Database: PostgreSQL
- ORM: SQLAlchemy
- ML: sentence-transformers for semantic course matching
- APIs: Coursera Course Catalog API
- Frontend: HTML, JavaScript, TailwindCSS

## Competency Scoring System

- 0-20: Beginner level
- 21-40: Foundational level
- 41-60: Intermediate level
- 61-80: Advanced level
- 81-100: Expert level

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure PostgreSQL:
   - Create a database named 'competency_assessment'
   - Update database credentials in app/database.py

4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

- POST `/assessments/start`: Start a new assessment
- GET `/questions/{session_id}`: Get the next question
- POST `/responses/{session_id}`: Submit an answer
- GET `/results/{session_id}`: Get assessment results
- GET `/recommendations/{session_id}`: Get personalized course recommendations
- POST `/admin/ingest-courses`: Manually trigger course data refresh

## Project Structure

```
.
├── app/
│   ├── data/
│   │   ├── fetch_real_courses.py    # Coursera API integration
│   │   ├── sample_questions.py      # Assessment questions
│   │   └── real_courses.json        # Cached course data
│   ├── models/
│   │   ├── assessment.py            # Assessment models
│   │   └── learning_resource.py     # Course models
│   ├── services/
│   │   ├── adaptive_engine.py       # Question selection
│   │   ├── course_ingestion.py      # Course processing
│   │   └── recommendation.py        # Course matching
│   ├── static/
│   │   ├── css/                    # Stylesheets
│   │   └── js/                     # Frontend logic
│   ├── templates/                   # HTML templates
│   ├── main.py                      # FastAPI application
│   └── routers/                     # API routes
├── requirements.txt                  # Project dependencies
└── README.md                        # Documentation
```
