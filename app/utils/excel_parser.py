import pandas as pd
import io
from typing import List, Dict, Any, Tuple

def parse_excel_quiz(file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses an Excel file containing quiz questions.
    Returns a list of question dicts and a list of error strings.
    """
    questions = []
    errors = []
    
    try:
        df = pd.read_excel(io.BytesIO(file_content))
    except Exception as e:
        return [], [f"Failed to read Excel file: {str(e)}"]

    # Basic column validation
    required_cols = ["Question Text", "Type", "Points", "Correct Answer"]
    for col in required_cols:
        if col not in df.columns:
            return [], [f"Missing required column: {col}"]

    for index, row in df.iterrows():
        try:
            q_text = str(row.get("Question Text", "")).strip()
            if not q_text:
                errors.append(f"Row {index+2}: Empty question text")
                continue

            # Standardize types
            raw_type = str(row.get("Type", "")).strip().upper()
            q_type = ""
            if raw_type in ["MCQ", "MULTIPLE CHOICE"]:
                q_type = "multiple_choice"
            elif raw_type in ["TF", "T/F", "TRUE FALSE", "TRUE/FALSE"]:
                q_type = "true_false"
            elif raw_type in ["SHORT", "SHORT ANSWER"]:
                q_type = "short_answer"
            else:
                errors.append(f"Row {index+2}: Invalid question type '{raw_type}'")
                continue

            points = float(row.get("Points", 1.0))
            correct_answer = str(row.get("Correct Answer", "")).strip()

            options = []
            if q_type == "multiple_choice":
                # Expect pipe-separated options
                raw_options = str(row.get("Options", ""))
                if not raw_options or raw_options == "nan":
                    errors.append(f"Row {index+2}: MCQ requires options")
                    continue
                
                parts = [p.strip() for p in raw_options.split('|') if p.strip()]
                if len(parts) < 2:
                    errors.append(f"Row {index+2}: MCQ needs at least 2 options")
                    continue
                
                # Check if correct answer is in options
                if correct_answer not in parts:
                    errors.append(f"Row {index+2}: Correct answer '{correct_answer}' not found in options")
                    continue
                
                options = [{"text": p, "is_correct": (p == correct_answer)} for p in parts]
            
            elif q_type == "true_false":
                # Standardize TF answer
                ca_upper = correct_answer.upper()
                correct_val_str = "" # To store "True" or "False" based on user input
                if ca_upper in ["TRUE", "T", "YES", "1"]:
                    correct_val_str = "True"
                elif ca_upper in ["FALSE", "F", "NO", "0"]:
                    correct_val_str = "False"
                else:
                    errors.append(f"Row {index+2}: Invalid T/F answer '{correct_answer}'")
                    continue
                
                # Always two options: True and False, assign IDs
                tf_parts = ["True", "False"]
                options = [{"id": chr(97 + i), "text": p, "is_correct": (p == correct_val_str)} for i, p in enumerate(tf_parts)]
            
            elif q_type == "short_answer":
                # For short answer, we store the correct string in the correct_answer field
                # In our data model, we might still use an option with text=correct_answer and is_correct=True
                options = [{"id": "correct", "text": correct_answer, "is_correct": True}]

            questions.append({
                "text": q_text,
                "question_type": q_type,
                "points": points,
                "options": options,
                "order": index
            })

        except Exception as e:
            errors.append(f"Row {index+2}: Unexpected error: {str(e)}")

    return questions, errors

def generate_template_excel() -> bytes:
    """Generates a sample Excel template."""
    data = [
        {
            "Question Text": "What is the capital of France?",
            "Type": "MCQ",
            "Points": 1.0,
            "Options": "Paris|London|Berlin|Madrid",
            "Correct Answer": "Paris"
        },
        {
            "Question Text": "The Earth is flat.",
            "Type": "TF",
            "Points": 1.0,
            "Options": "",
            "Correct Answer": "False"
        },
        {
            "Question Text": "Which programming language is this backend written in?",
            "Type": "Short",
            "Points": 2.0,
            "Options": "",
            "Correct Answer": "Python"
        }
    ]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()
