import uuid
from typing import Dict, Any

# In-memory storage for background jobs
# In a production app, this would be Redis or a database
jobs: Dict[str, Dict[str, Any]] = {}

def create_job(total_items: int, quiz_id: str) -> str:
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "quiz_id": quiz_id,
        "status": "processing",
        "progress": 0,
        "total": total_items,
        "completed": 0,
        "results": {
            "total": 0,
            "mcq": 0,
            "tf": 0,
            "short": 0,
            "failed": 0,
            "errors": []
        }
    }
    return job_id

def update_job_progress(job_id: str, completed: int, error: str = None, q_type: str = None):
    if job_id not in jobs:
        return
    
    job = jobs[job_id]
    job["completed"] = completed
    job["progress"] = int((completed / job["total"]) * 100) if job["total"] > 0 else 100
    
    if error:
        job["results"]["failed"] += 1
        job["results"]["errors"].append(error)
    elif q_type:
        job["results"]["total"] += 1
        if q_type == "multiple_choice":
            job["results"]["mcq"] += 1
        elif q_type == "true_false":
            job["results"]["tf"] += 1
        elif q_type == "short_answer":
            job["results"]["short"] += 1

def complete_job(job_id: str):
    if job_id in jobs:
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100

def get_job_status(job_id: str) -> Dict[str, Any]:
    return jobs.get(job_id)
