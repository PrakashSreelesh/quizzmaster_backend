"""
Test Quiz CRUD — create, list, get, update, delete, questions, role enforcement, answer stripping.
"""
import pytest


class TestQuizCRUD:
    def test_create_quiz(self, client, instructor_headers):
        response = client.post("/api/v1/quizzes/", json={
            "title": "New Quiz",
            "description": "A test quiz",
            "time_limit_minutes": 15,
        }, headers=instructor_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Quiz"
        assert data["is_published"] is False

    def test_create_quiz_student_forbidden(self, client, student_headers):
        response = client.post("/api/v1/quizzes/", json={
            "title": "Student Quiz",
        }, headers=student_headers)
        assert response.status_code == 403

    def test_create_quiz_unauthenticated(self, client):
        response = client.post("/api/v1/quizzes/", json={"title": "No Auth"})
        assert response.status_code == 401

    def test_list_my_quizzes(self, client, instructor_headers, sample_quiz):
        response = client.get("/api/v1/quizzes/my", headers=instructor_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Python Basics Quiz"
        assert data[0]["question_count"] == 3

    def test_get_quiz(self, client, instructor_headers, sample_quiz):
        response = client.get(f"/api/v1/quizzes/{sample_quiz.id}", headers=instructor_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Python Basics Quiz"
        assert len(data["questions"]) == 3
        # Instructor can see is_correct
        assert any(
            opt.get("is_correct") is True
            for q in data["questions"]
            for opt in q.get("options", [])
            if "is_correct" in opt
        )

    def test_get_quiz_not_found(self, client, instructor_headers):
        response = client.get("/api/v1/quizzes/99999", headers=instructor_headers)
        assert response.status_code == 404

    def test_update_quiz(self, client, instructor_headers, sample_quiz):
        response = client.put(f"/api/v1/quizzes/{sample_quiz.id}", json={
            "title": "Updated Title",
            "description": "Updated description",
        }, headers=instructor_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_publish_quiz(self, client, instructor_headers, sample_quiz):
        response = client.put(f"/api/v1/quizzes/{sample_quiz.id}", json={
            "is_published": True,
        }, headers=instructor_headers)
        assert response.status_code == 200
        assert response.json()["is_published"] is True

    def test_delete_quiz(self, client, instructor_headers, sample_quiz):
        response = client.delete(f"/api/v1/quizzes/{sample_quiz.id}", headers=instructor_headers)
        assert response.status_code == 204
        # Verify it's gone
        response = client.get(f"/api/v1/quizzes/{sample_quiz.id}", headers=instructor_headers)
        assert response.status_code == 404

    def test_delete_quiz_not_found(self, client, instructor_headers):
        response = client.delete("/api/v1/quizzes/99999", headers=instructor_headers)
        assert response.status_code == 404


class TestPublishedQuizzes:
    def test_list_published_quizzes(self, client, student_headers, published_quiz):
        response = client.get("/api/v1/quizzes/published", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["is_published"] is True

    def test_list_published_no_unpublished(self, client, student_headers, sample_quiz):
        # sample_quiz is not published
        response = client.get("/api/v1/quizzes/published", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_published_quiz_strips_answers(self, client, student_headers, published_quiz):
        response = client.get(
            f"/api/v1/quizzes/published/{published_quiz.id}",
            headers=student_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # is_correct should NOT be in any option
        for question in data["questions"]:
            for option in question.get("options", []):
                assert "is_correct" not in option

    def test_get_unpublished_quiz_fails(self, client, student_headers, sample_quiz):
        response = client.get(
            f"/api/v1/quizzes/published/{sample_quiz.id}",
            headers=student_headers,
        )
        assert response.status_code == 404


class TestQuestionManagement:
    def test_add_question(self, client, instructor_headers, sample_quiz):
        response = client.post(f"/api/v1/quizzes/{sample_quiz.id}/questions", json={
            "text": "New question?",
            "question_type": "true_false",
            "points": 1.0,
            "order": 3,
            "options": [
                {"id": "true", "text": "True", "is_correct": True},
                {"id": "false", "text": "False", "is_correct": False},
            ],
        }, headers=instructor_headers)
        assert response.status_code == 201
        assert response.json()["text"] == "New question?"

    def test_add_question_invalid_type(self, client, instructor_headers, sample_quiz):
        response = client.post(f"/api/v1/quizzes/{sample_quiz.id}/questions", json={
            "text": "Bad type?",
            "question_type": "essay",
            "points": 1.0,
        }, headers=instructor_headers)
        assert response.status_code == 422

    def test_update_question(self, client, instructor_headers, sample_quiz, db):
        question = sample_quiz.questions[0]
        response = client.put(
            f"/api/v1/quizzes/{sample_quiz.id}/questions/{question.id}",
            json={"text": "Updated text"},
            headers=instructor_headers,
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Updated text"

    def test_delete_question(self, client, instructor_headers, sample_quiz, db):
        question = sample_quiz.questions[0]
        response = client.delete(
            f"/api/v1/quizzes/{sample_quiz.id}/questions/{question.id}",
            headers=instructor_headers,
        )
        assert response.status_code == 204

    def test_add_question_student_forbidden(self, client, student_headers, sample_quiz):
        response = client.post(f"/api/v1/quizzes/{sample_quiz.id}/questions", json={
            "text": "Student Q?",
            "question_type": "true_false",
        }, headers=student_headers)
        assert response.status_code == 403

    def test_question_not_found(self, client, instructor_headers, sample_quiz):
        response = client.put(
            f"/api/v1/quizzes/{sample_quiz.id}/questions/99999",
            json={"text": "Updated"},
            headers=instructor_headers,
        )
        assert response.status_code == 404
