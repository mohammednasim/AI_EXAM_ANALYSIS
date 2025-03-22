#mcq_generator.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
import PyPDF2
import re

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))


def extract_text(file_path):
    """Extracts text from a PDF file."""
    import PyPDF2
    text = ""
    try:
        with open(file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        return f"Error extracting text: {str(e)}"
    return text.strip()


def evaluate_single_pdf(file_path):
    """Evaluate student answers from a single PDF file with detailed analysis."""
    extracted_text = extract_text(file_path)
    mcqs = extract_mcqs_from_pdf(extracted_text)

    if not mcqs or (len(mcqs) == 1 and 'error' in mcqs[0]):
        return {"error": "Could not extract MCQs from the PDF. Please check the format."}

    # Initialize evaluation structure
    evaluation = {
        "student_answers": [],
        "correct_answers": [],
        "score": {"correct": 0, "total": len(mcqs), "percentage": 0},
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": [],
        "specialty_performance": {},
        "upsc_fit_assessment": ""
    }

    # Initialize categories based on UPSC pattern
    categories = {
        "General Knowledge & Current Affairs": [],
        "Indian Polity & Governance": [],
        "Indian Economy": [],
        "Geography & Environment": [],
        "Science & Technology": []
    }

    # Determine question category based on number ranges
    for mcq in mcqs:
        q_num = 0
        if isinstance(mcq.get('question_num', ''), str) and mcq['question_num'].isdigit():
            q_num = int(mcq['question_num'])
        elif isinstance(mcq.get('question_num', ''), int):
            q_num = mcq['question_num']

        # Assign category based on question number ranges
        if 1 <= q_num <= 5:
            category = "General Knowledge & Current Affairs"
        elif 6 <= q_num <= 10:
            category = "Indian Polity & Governance"
        elif 11 <= q_num <= 15:
            category = "Indian Economy"
        elif 16 <= q_num <= 20:
            category = "Geography & Environment"
        elif 21 <= q_num <= 25:
            category = "Science & Technology"
        else:
            # Default category if question number doesn't fit known ranges
            category = "Miscellaneous"
            if "Miscellaneous" not in categories:
                categories["Miscellaneous"] = []

        # Store question in its category
        if category in categories:
            categories[category].append(mcq)

        student_answer = mcq.get('student_answer', '').strip()
        correct_answer = mcq.get('correct_answer', '').strip()

        evaluation["student_answers"].append(
            {"question_num": mcq['question_num'], "selected_option": student_answer, "question": mcq['question']})
        evaluation["correct_answers"].append(
            {"question_num": mcq['question_num'], "correct_option": correct_answer, "question": mcq['question']})

        if student_answer.upper() == correct_answer.upper():
            evaluation["score"]["correct"] += 1

    # Calculate overall score
    evaluation["score"]["percentage"] = (evaluation["score"]["correct"] / evaluation["score"]["total"]) * 100 if \
    evaluation["score"]["total"] > 0 else 0

    # Calculate category-wise performance
    for category, questions in categories.items():
        if questions:  # Only process categories with questions
            correct = sum(
                1 for q in questions if q.get('student_answer', '').upper() == q.get('correct_answer', '').upper())
            total = len(questions)
            percentage = (correct / total) * 100 if total > 0 else 0

            evaluation["specialty_performance"][category] = {
                "correct": correct,
                "total": total,
                "percentage": percentage
            }

    # Identify strengths and weaknesses based on category performance
    for category, perf in evaluation["specialty_performance"].items():
        if perf["percentage"] >= 80:
            evaluation["strengths"].append(f"Strong understanding of {category} ({perf['percentage']:.1f}%)")
        elif perf["percentage"] <= 40:
            evaluation["weaknesses"].append(f"Needs significant improvement in {category} ({perf['percentage']:.1f}%)")
            evaluation["improvement_suggestions"].append(
                f"Focus on studying {category} concepts and practice more questions in this area")
        elif perf["percentage"] < 60:
            evaluation["weaknesses"].append(f"Below average performance in {category} ({perf['percentage']:.1f}%)")
            evaluation["improvement_suggestions"].append(f"Review basic concepts in {category} and practice regularly")

    # UPSC fit assessment
    if evaluation["score"]["percentage"] >= 75:
        evaluation[
            "upsc_fit_assessment"] = "Based on your performance, you show good potential for the UPSC examination. Your overall score indicates a strong foundation in the tested subjects."
    elif evaluation["score"]["percentage"] >= 60:
        evaluation[
            "upsc_fit_assessment"] = "You show moderate potential for the UPSC examination. With focused preparation in your weaker areas, you can improve your chances significantly."
    else:
        evaluation[
            "upsc_fit_assessment"] = "Your current performance suggests you need substantial preparation before attempting the UPSC examination. Focus on building a stronger foundation in all subjects, particularly in your weaker areas."

    # Add general feedback based on performance
    if evaluation["score"]["percentage"] >= 85:
        evaluation["strengths"].append(
            "Excellent overall performance! You've demonstrated a strong grasp of most subjects.")
    elif evaluation["score"]["percentage"] >= 70:
        evaluation["strengths"].append("Good overall performance. You have a solid foundation in most areas.")
    elif evaluation["score"]["percentage"] >= 50:
        evaluation["strengths"].append("Average overall performance. You have a basic understanding of most subjects.")
    else:
        evaluation["weaknesses"].append(
            "Overall performance needs significant improvement. Consider a structured study plan.")

    # Add generic improvement suggestions if none were added from category analysis
    if not evaluation["improvement_suggestions"]:
        evaluation["improvement_suggestions"].append("Review incorrect answers and understand the underlying concepts")
        evaluation["improvement_suggestions"].append(
            "Practice questions from previous year papers to improve test-taking skills")
        evaluation["improvement_suggestions"].append("Create a structured study plan focusing on your weaker areas")

    return evaluation

import re


# In mcq_generator.py, update the extract_mcqs_from_pdf function:

def extract_mcqs_from_pdf(text):
    """Extracts existing MCQs from PDF text without changing them."""
    # Regex patterns for different question formats
    patterns = [
        r'(\d+)\.\s+(.*?)(?:\n|\r\n?)(A\)[.\s]+(.*?)(?:\n|\r\n?)B\)[.\s]+(.*?)(?:\n|\r\n?)C\)[.\s]+(.*?)(?:\n|\r\n?)D\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer:\s*([A-D]))(?:\n|\r\n?)(Correct Answer:\s*([A-D]))(?=\n\d+\.\s+|\Z)',
        r'(Q\.\s*\d+)\.\s+(.*?)(?:\n|\r\n?)(\(a\)[.\s]+(.*?)(?:\n|\r\n?)\(b\)[.\s]+(.*?)(?:\n|\r\n?)\(c\)[.\s]+(.*?)(?:\n|\r\n?)\(d\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer:\s*([a-d]))(?:\n|\r\n?)(Correct Answer:\s*([a-d]))(?=\n\s*Q\.\s*\d+|$)',
    ]

    mcqs = []

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            question_num = match.group(1).strip()
            question_text = match.group(2).strip()
            options_text = match.group(3).strip() if len(match.groups()) >= 3 else ""

            # Extract individual options in a cleaner format
            options = []
            if 'A)' in options_text or 'A.' in options_text:
                option_matches = re.findall(r'([A-D][.\s)])(.*?)(?=(?:[A-D][.\s)])|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"{opt_letter} {opt_text.strip()}")
            elif '(a)' in options_text or '(a)' in options_text:
                option_matches = re.findall(r'\((a|b|c|d)\)[.\s)](.*?)(?=\([a-d]\)|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"({opt_letter}) {opt_text.strip()}")

            # If no options were extracted but we have the text, add it as is
            if not options and options_text:
                options = [options_text]

            # Default to medium difficulty if not specified
            difficulty = "MEDIUM"

            # Extract student and correct answers
            student_answer = ""
            correct_answer = ""

            # Update the regex for answers to capture the letters properly
            if len(match.groups()) >= 9 and match.group(8):
                student_answer = match.group(9).strip().upper() if match.group(9) else ""

            if len(match.groups()) >= 11 and match.group(10):
                correct_answer = match.group(11).strip().upper() if match.group(11) else ""

            mcq = {
                'question_num': question_num,
                'question': question_text,
                'options': ", ".join(options),  # Join options with our separator
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'difficulty': difficulty
            }

            mcqs.append(mcq)

    # If no MCQs were extracted with the patterns, use AI to help extract
    if len(mcqs) == 0:
        mcqs = ai_extract_mcqs(text)

    return mcqs
def ai_extract_mcqs(text):
    """Use AI to extract MCQs when standard patterns fail."""
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
    Extract all existing multiple-choice questions from the following text. 
    DO NOT create new questions, only extract what's already there.

    For each question found, follow this exact format:

    [Question Number]: The question number from the document
    [Question]: The question text here?
    [Options]: A) Option A text//@ B) Option B text//@ C) Option C text//@ D) Option D text
    [Student Answer]: The letter of the student's answer (A, B, C, or D)
    [Correct Answer]: The letter of the correct option (A, B, C, or D)
    [Difficulty Level]: EASY or MEDIUM or HARD (assign an appropriate difficulty level)

    Important: 
    1. Use //@ as the separator between options.
    2. Keep the original question text and options EXACTLY as they appear in the document.
    3. Include the option letter (A, B, C, D) with each option.
    4. For Student Answer and Correct Answer, extract ONLY the letter (A, B, C, or D).
    5. The difficulty level should be one of: EASY, MEDIUM, or HARD based on the complexity of the question.

    TEXT:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        mcq_text = response.text.strip()

        # Extract MCQs from the response
        mcqs = []

        # Split by double newlines to separate questions
        questions_raw = re.split(r'\n\n+', mcq_text)

        for q_block in questions_raw:
            lines = q_block.strip().split('\n')
            mcq = {}

            for line in lines:
                if line.startswith('[Question Number]:'):
                    mcq['question_num'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Question]:'):
                    mcq['question'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Options]:'):
                    mcq['options'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Student Answer]:'):
                    mcq['student_answer'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Correct Answer]:'):
                    mcq['correct_answer'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Difficulty Level]:'):
                    mcq['difficulty'] = line[line.find(':') + 1:].strip()

            # Only add if we have required fields
            if 'question' in mcq and 'options' in mcq:
                # Set default values if missing
                if 'question_num' not in mcq:
                    mcq['question_num'] = str(len(mcqs) + 1)
                if 'student_answer' not in mcq:
                    mcq['student_answer'] = ""
                if 'correct_answer' not in mcq:
                    mcq['correct_answer'] = ""
                if 'difficulty' not in mcq:
                    mcq['difficulty'] = "MEDIUM"

                mcqs.append(mcq)

        return mcqs
    except Exception as e:
        return [{"error": f"Error extracting MCQs: {str(e)}"}]


def generate_mcqs(text, num_questions=5):
    """Legacy function to generate new MCQs. Kept for backwards compatibility."""
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
    Generate {num_questions} multiple-choice questions (MCQs) from the following text.
    Each MCQ should have 4 options and one correct answer.

    For each question, follow this exact format:

    [Question]: The question text here?
    [Options]: Option A//@ Option B//@ Option C//@ Option D
    [Correct Answer]: The correct option text here
    [Difficulty Level]: EASY or MEDIUM or HARD (assign an appropriate difficulty level)

    Important: 
    1. Make sure to use //@ as the separator between options. 
    2. The difficulty level should be one of: EASY, MEDIUM, or HARD based on the complexity of the question.
    3. Include a good mix of all three difficulty levels.

    TEXT:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        mcq_text = response.text.strip()

        # Extract MCQs from the response
        mcqs = []

        # Split by double newlines to separate questions
        questions_raw = re.split(r'\n\n+', mcq_text)

        for q_block in questions_raw:
            lines = q_block.strip().split('\n')
            mcq = {}

            for line in lines:
                if line.startswith('[Question]:'):
                    mcq['question'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Options]:'):
                    mcq['options'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Correct Answer]:'):
                    mcq['answer'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Difficulty Level]:'):
                    mcq['difficulty'] = line[line.find(':') + 1:].strip()

            # Only add if we have all required fields
            if all(k in mcq for k in ['question', 'options', 'answer', 'difficulty']):
                mcqs.append(mcq)

        return mcqs
    except Exception as e:
        return [{"error": f"Error generating MCQs: {str(e)}"}]