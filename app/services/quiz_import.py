from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Question
from app.core.jobs import update_job_progress, complete_job, get_job_status

def process_quiz_import(job_id: str, quiz_id: str, questions_data: list):
    """
    Background task to create questions from parsed data.
    Updates the job status incrementally.
    """
    db = SessionLocal()
    try:
        for i, q_data in enumerate(questions_data):
            try:
                question = Question(
                    quiz_id=quiz_id,
                    text=q_data["text"],
                    question_type=q_data["question_type"],
                    points=q_data["points"],
                    order=q_data["order"],
                    options=q_data["options"]
                )
                db.add(question)
                db.commit()
                update_job_progress(job_id, i + 1, q_type=q_data["question_type"])
            except Exception as e:
                db.rollback()
                update_job_progress(job_id, i + 1, error=f"Row {i+1}: {str(e)}")
        
        complete_job(job_id)
    except Exception as e:
        # Fallback for unexpected errors at the loop level
        update_job_progress(job_id, 0, error=f"Critical error: {str(e)}")
    finally:
        db.close()
