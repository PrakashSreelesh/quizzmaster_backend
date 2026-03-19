"""
Test Grading Service — unit tests for grading logic in isolation.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.services.grading import _grade_choice, _grade_short_answer, grade_submission


class TestGradeChoice:
    def test_correct_choice(self):
        options = [
            {"id": "a", "text": "Wrong", "is_correct": False},
            {"id": "b", "text": "Right", "is_correct": True},
        ]
        assert _grade_choice("b", options) is True

    def test_incorrect_choice(self):
        options = [
            {"id": "a", "text": "Wrong", "is_correct": False},
            {"id": "b", "text": "Right", "is_correct": True},
        ]
        assert _grade_choice("a", options) is False

    def test_empty_answer(self):
        options = [{"id": "a", "text": "Answer", "is_correct": True}]
        assert _grade_choice("", options) is False

    def test_none_answer(self):
        options = [{"id": "a", "text": "Answer", "is_correct": True}]
        assert _grade_choice(None, options) is False

    def test_empty_options(self):
        assert _grade_choice("a", []) is False

    def test_true_false_correct(self):
        options = [
            {"id": "true", "text": "True", "is_correct": True},
            {"id": "false", "text": "False", "is_correct": False},
        ]
        assert _grade_choice("true", options) is True

    def test_true_false_incorrect(self):
        options = [
            {"id": "true", "text": "True", "is_correct": False},
            {"id": "false", "text": "False", "is_correct": True},
        ]
        assert _grade_choice("true", options) is False


class TestGradeShortAnswer:
    def test_exact_match(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer("Paris", options) is True

    def test_case_insensitive(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer("paris", options) is True
        assert _grade_short_answer("PARIS", options) is True

    def test_whitespace_stripped(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer("  Paris  ", options) is True

    def test_incorrect_answer(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer("London", options) is False

    def test_empty_answer(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer("", options) is False

    def test_none_answer(self):
        options = [{"text": "Paris"}]
        assert _grade_short_answer(None, options) is False

    def test_multiple_accepted_answers(self):
        options = [{"text": "Paris"}, {"text": "paris"}, {"text": "Ville de Paris"}]
        assert _grade_short_answer("Ville de Paris", options) is True


class TestGradeSubmission:
    def _make_mock_submission(self, answers_data):
        """Create mock submission with answers."""
        submission = MagicMock()
        submission.answers = []
        for ad in answers_data:
            ans = MagicMock()
            ans.question_id = ad["question_id"]
            ans.answer_value = ad.get("answer_value")
            ans.is_correct = None
            ans.points_awarded = None
            submission.answers.append(ans)
        submission.score = None
        submission.max_score = None
        submission.percentage = None
        submission.graded_at = None
        return submission

    def _make_mock_quiz(self, questions_data):
        """Create mock quiz with questions."""
        quiz = MagicMock()
        quiz.questions = []
        for qd in questions_data:
            q = MagicMock()
            q.id = qd["id"]
            q.question_type = qd["question_type"]
            q.points = qd["points"]
            q.options = qd["options"]
            quiz.questions.append(q)
        return quiz

    def test_all_correct(self):
        quiz = self._make_mock_quiz([
            {
                "id": 1, "question_type": "multiple_choice", "points": 1.0,
                "options": [
                    {"id": "a", "text": "Wrong", "is_correct": False},
                    {"id": "b", "text": "Right", "is_correct": True},
                ],
            },
            {
                "id": 2, "question_type": "short_answer", "points": 2.0,
                "options": [{"text": "Paris"}],
            },
        ])
        submission = self._make_mock_submission([
            {"question_id": 1, "answer_value": "b"},
            {"question_id": 2, "answer_value": "Paris"},
        ])
        db = MagicMock()

        result = grade_submission(submission, quiz, db)
        assert result.score == 3.0
        assert result.max_score == 3.0
        assert result.percentage == 100.0

    def test_all_wrong(self):
        quiz = self._make_mock_quiz([
            {
                "id": 1, "question_type": "multiple_choice", "points": 1.0,
                "options": [
                    {"id": "a", "text": "Wrong", "is_correct": False},
                    {"id": "b", "text": "Right", "is_correct": True},
                ],
            },
        ])
        submission = self._make_mock_submission([
            {"question_id": 1, "answer_value": "a"},
        ])
        db = MagicMock()

        result = grade_submission(submission, quiz, db)
        assert result.score == 0.0
        assert result.percentage == 0.0

    def test_unknown_question_id(self):
        quiz = self._make_mock_quiz([
            {
                "id": 1, "question_type": "multiple_choice", "points": 1.0,
                "options": [{"id": "a", "text": "A", "is_correct": True}],
            },
        ])
        submission = self._make_mock_submission([
            {"question_id": 999, "answer_value": "a"},
        ])
        db = MagicMock()

        result = grade_submission(submission, quiz, db)
        # Unknown question scores 0, but max_score includes only Q1
        assert result.answers[0].is_correct is False
        assert result.answers[0].points_awarded == 0.0

    def test_null_answer_value(self):
        quiz = self._make_mock_quiz([
            {
                "id": 1, "question_type": "multiple_choice", "points": 1.0,
                "options": [{"id": "a", "text": "A", "is_correct": True}],
            },
        ])
        submission = self._make_mock_submission([
            {"question_id": 1, "answer_value": None},
        ])
        db = MagicMock()

        result = grade_submission(submission, quiz, db)
        assert result.score == 0.0
        assert result.answers[0].is_correct is False
