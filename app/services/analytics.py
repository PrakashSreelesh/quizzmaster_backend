"""
QuizzMaster Backend - Analytics Service
Score aggregation and statistics computation.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import User, Quiz, Question, Submission, Answer
from app.schemas import (
    QuizAnalytics, QuestionStat, StudentAnalytics, RecentSubmission,
    PlatformSummary, LeaderboardEntry,
)


def get_quiz_analytics(quiz: Quiz, db: Session) -> QuizAnalytics:
    """Compute analytics for a specific quiz."""
    submissions = (
        db.query(Submission)
        .filter(Submission.quiz_id == quiz.id, Submission.graded_at.isnot(None))
        .all()
    )

    total = len(submissions)

    if total == 0:
        return QuizAnalytics(
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            total_submissions=0,
            average_score=0.0,
            average_percentage=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            pass_rate=0.0,
            question_stats=[],
        )

    scores = [s.score for s in submissions if s.score is not None]
    percentages = [s.percentage for s in submissions if s.percentage is not None]

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_percentage = sum(percentages) / len(percentages) if percentages else 0.0
    highest = max(scores) if scores else 0.0
    lowest = min(scores) if scores else 0.0
    passed = sum(1 for p in percentages if p >= 60.0)
    pass_rate = (passed / total * 100) if total > 0 else 0.0

    # Per-question stats
    question_stats = []
    questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()
    for q in questions:
        answers = (
            db.query(Answer)
            .join(Submission)
            .filter(
                Answer.question_id == q.id,
                Submission.quiz_id == quiz.id,
                Submission.graded_at.isnot(None),
            )
            .all()
        )
        total_answers = len(answers)
        correct = sum(1 for a in answers if a.is_correct)
        rate = (correct / total_answers * 100) if total_answers > 0 else 0.0
        question_stats.append(QuestionStat(
            question_id=q.id,
            question_text=q.text,
            total_answers=total_answers,
            correct_answers=correct,
            correct_rate=round(rate, 2),
        ))

    max_score = sum(q.points for q in questions)
    
    return QuizAnalytics(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        total_submissions=total,
        average_score=round(avg_score, 2),
        max_score=max_score,
        average_percentage=round(avg_percentage, 2),
        highest_score=highest,
        lowest_score=lowest,
        pass_rate=round(pass_rate, 2),
        question_stats=question_stats,
    )


def get_student_analytics(user: User, db: Session) -> StudentAnalytics:
    """Compute personal performance stats for a student."""
    submissions = (
        db.query(Submission)
        .filter(Submission.student_id == user.id, Submission.graded_at.isnot(None))
        .options(joinedload(Submission.quiz))
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    total = len(submissions)
    percentages = [s.percentage for s in submissions if s.percentage is not None]
    avg_pct = sum(percentages) / len(percentages) if percentages else 0.0
    passed = sum(1 for p in percentages if p >= 60.0)
    failed = total - passed

    recent = []
    for s in submissions[:5]:
        recent.append(RecentSubmission(
            id=s.id,
            quiz_id=s.quiz_id,
            quiz_title=s.quiz.title if s.quiz else "Unknown",
            score=s.score or 0.0,
            max_score=s.max_score or 0.0,
            percentage=s.percentage or 0.0,
            submitted_at=s.submitted_at,
        ))

    return StudentAnalytics(
        total_submissions=total,
        average_percentage=round(avg_pct, 2),
        quizzes_passed=passed,
        quizzes_failed=failed,
        recent_submissions=recent,
    )


def get_quiz_leaderboard(quiz_id: str, db: Session) -> list:
    """Get ranked leaderboard for a specific quiz."""
    submissions = (
        db.query(Submission)
        .filter(Submission.quiz_id == quiz_id, Submission.graded_at.isnot(None))
        .options(joinedload(Submission.student))
        .order_by(Submission.score.desc())
        .all()
    )

    leaderboard = []
    for rank, sub in enumerate(submissions, 1):
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            student_id=sub.student_id,
            student_name=sub.student.username if sub.student else "Unknown",
            score=sub.score or 0.0,
            percentage=sub.percentage or 0.0,
            submitted_at=sub.submitted_at,
        ))

    return leaderboard


def get_platform_summary(db: Session) -> PlatformSummary:
    """Get platform-wide summary statistics."""
    total_quizzes = db.query(Quiz).count()
    total_published = db.query(Quiz).filter(Quiz.is_published == True).count()
    total_submissions = db.query(Submission).filter(Submission.graded_at.isnot(None)).count()
    total_students = db.query(User).filter(User.role == "student").count()
    total_instructors = db.query(User).filter(User.role == "instructor").count()

    # Overall pass rate
    graded = (
        db.query(Submission)
        .filter(Submission.graded_at.isnot(None), Submission.percentage.isnot(None))
        .all()
    )
    if graded:
        passed = sum(1 for s in graded if s.percentage >= 60.0)
        overall_pass_rate = (passed / len(graded) * 100)
    else:
        overall_pass_rate = 0.0

    return PlatformSummary(
        total_quizzes=total_quizzes,
        total_published_quizzes=total_published,
        total_submissions=total_submissions,
        total_students=total_students,
        total_instructors=total_instructors,
        overall_pass_rate=round(overall_pass_rate, 2),
    )
