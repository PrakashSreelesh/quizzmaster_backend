"""
Test Analytics — quiz analytics, student analytics, platform summary, role guards.
"""
import pytest


class TestQuizAnalytics:
    def test_quiz_analytics_no_submissions(
        self, client, instructor_headers, published_quiz
    ):
        response = client.get(
            f"/api/v1/analytics/quiz/{published_quiz.id}",
            headers=instructor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_submissions"] == 0
        assert data["average_score"] == 0.0

    def test_quiz_analytics_with_submissions(
        self, client, instructor_headers, student_headers, published_quiz
    ):
        questions = published_quiz.questions
        # Student submits
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
                {"question_id": questions[1].id, "answer_value": "false"},
                {"question_id": questions[2].id, "answer_value": "Paris"},
            ],
        }, headers=student_headers)

        response = client.get(
            f"/api/v1/analytics/quiz/{published_quiz.id}",
            headers=instructor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_submissions"] == 1
        assert data["average_score"] == 4.0
        assert data["pass_rate"] == 100.0
        assert len(data["question_stats"]) == 3

    def test_quiz_analytics_student_forbidden(
        self, client, student_headers, published_quiz
    ):
        response = client.get(
            f"/api/v1/analytics/quiz/{published_quiz.id}",
            headers=student_headers,
        )
        assert response.status_code == 403

    def test_quiz_analytics_not_found(self, client, instructor_headers):
        response = client.get(
            "/api/v1/analytics/quiz/99999",
            headers=instructor_headers,
        )
        assert response.status_code == 404


class TestStudentAnalytics:
    def test_student_analytics_no_submissions(self, client, student_headers):
        response = client.get("/api/v1/analytics/me", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_submissions"] == 0
        assert data["average_percentage"] == 0.0

    def test_student_analytics_with_submissions(
        self, client, student_headers, published_quiz
    ):
        questions = published_quiz.questions
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
                {"question_id": questions[1].id, "answer_value": "false"},
                {"question_id": questions[2].id, "answer_value": "Paris"},
            ],
        }, headers=student_headers)

        response = client.get("/api/v1/analytics/me", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_submissions"] == 1
        assert data["average_percentage"] == 100.0
        assert data["quizzes_passed"] == 1


class TestLeaderboard:
    def test_quiz_leaderboard(
        self, client, instructor_headers, student_headers, second_student_headers,
        published_quiz,
    ):
        questions = published_quiz.questions
        # Two students submit
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
                {"question_id": questions[1].id, "answer_value": "false"},
                {"question_id": questions[2].id, "answer_value": "Paris"},
            ],
        }, headers=student_headers)
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "a"},
                {"question_id": questions[1].id, "answer_value": "true"},
                {"question_id": questions[2].id, "answer_value": "London"},
            ],
        }, headers=second_student_headers)

        response = client.get(
            f"/api/v1/analytics/quiz/{published_quiz.id}/leaderboard",
            headers=instructor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # First should have higher score
        assert data[0]["rank"] == 1
        assert data[0]["score"] >= data[1]["score"]


class TestPlatformSummary:
    def test_platform_summary(self, client, student_headers, published_quiz):
        response = client.get("/api/v1/analytics/platform", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_quizzes" in data
        assert "total_submissions" in data
        assert "overall_pass_rate" in data
