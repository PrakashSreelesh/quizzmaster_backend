"""
Test Submissions — submit quiz, grading, duplicate detection, access control.
"""
import pytest


class TestSubmitQuiz:
    def test_submit_quiz_success(self, client, student_headers, published_quiz):
        questions = published_quiz.questions
        response = client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},      # correct
                {"question_id": questions[1].id, "answer_value": "false"},   # correct
                {"question_id": questions[2].id, "answer_value": "Paris"},   # correct
            ],
        }, headers=student_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["score"] == 4.0  # 1 + 1 + 2
        assert data["max_score"] == 4.0
        assert data["percentage"] == 100.0

    def test_submit_quiz_partial_score(self, client, student_headers, published_quiz):
        questions = published_quiz.questions
        response = client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "a"},      # wrong
                {"question_id": questions[1].id, "answer_value": "false"},   # correct
                {"question_id": questions[2].id, "answer_value": "London"}, # wrong
            ],
        }, headers=student_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["score"] == 1.0  # only Q2 correct
        assert data["percentage"] == 25.0

    def test_submit_quiz_duplicate_rejected(self, client, student_headers, published_quiz):
        questions = published_quiz.questions
        # First submission
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
            ],
        }, headers=student_headers)
        # Second submission — should fail
        response = client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
            ],
        }, headers=student_headers)
        assert response.status_code == 409

    def test_submit_unpublished_quiz(self, client, student_headers, sample_quiz):
        response = client.post(f"/api/v1/submissions/quiz/{sample_quiz.id}", json={
            "answers": [],
        }, headers=student_headers)
        assert response.status_code == 404

    def test_submit_nonexistent_quiz(self, client, student_headers):
        response = client.post("/api/v1/submissions/quiz/99999", json={
            "answers": [],
        }, headers=student_headers)
        assert response.status_code == 404


class TestListSubmissions:
    def test_list_my_submissions(self, client, student_headers, published_quiz):
        questions = published_quiz.questions
        # Submit first
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
            ],
        }, headers=student_headers)
        # List
        response = client.get("/api/v1/submissions/my", headers=student_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_my_submission(self, client, student_headers, published_quiz):
        questions = published_quiz.questions
        sub_resp = client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
            ],
        }, headers=student_headers)
        sub_id = sub_resp.json()["id"]
        response = client.get(f"/api/v1/submissions/my/{sub_id}", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["quiz_title"] == "Python Basics Quiz"
        assert len(data["answers"]) >= 1

    def test_instructor_view_quiz_submissions(
        self, client, instructor_headers, student_headers, published_quiz
    ):
        questions = published_quiz.questions
        # Student submits
        client.post(f"/api/v1/submissions/quiz/{published_quiz.id}", json={
            "answers": [
                {"question_id": questions[0].id, "answer_value": "b"},
            ],
        }, headers=student_headers)
        # Instructor views
        response = client.get(
            f"/api/v1/submissions/quiz/{published_quiz.id}",
            headers=instructor_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_student_cannot_view_quiz_submissions(
        self, client, student_headers, published_quiz
    ):
        response = client.get(
            f"/api/v1/submissions/quiz/{published_quiz.id}",
            headers=student_headers,
        )
        assert response.status_code == 403
