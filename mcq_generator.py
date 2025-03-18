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

def extract_mcqs_from_pdf(text):
    """Extracts existing MCQs from PDF text without changing them."""
    patterns = [
        r'(\d+)\.\s+(.*?)(?:\n|\r\n?)(A\)[.\s]+(.*?)(?:\n|\r\n?)B\)[.\s]+(.*?)(?:\n|\r\n?)C\)[.\s]+(.*?)(?:\n|\r\n?)D\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer: [a-d]\)[^\n\r]+)(?:\n|\r\n?)(Correct Answer: [a-d]\)[^\n\r]+)(?=\n\d+\.\s+|\Z)',
        r'(Q\.\s*\d+)\.\s+(.*?)(?:\n|\r\n?)(\(a\)[.\s]+(.*?)(?:\n|\r\n?)\(b\)[.\s]+(.*?)(?:\n|\r\n?)\(c\)[.\s]+(.*?)(?:\n|\r\n?)\(d\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer: [a-d]\)[^\n\r]+)(?:\n|\r\n?)(Correct Answer: [a-d]\)[^\n\r]+)(?=\n\s*Q\.\s*\d+|$)',
    ]

    mcqs = []

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            question_num = match.group(1).strip()
            question_text = match.group(2).strip()
            options_text = ""

            # Extract options
            if len(match.groups()) >= 4:
                options_text = "A) " + match.group(3).strip() + "\nB) " + match.group(
                    4).strip() + "\nC) " + match.group(5).strip() + "\nD) " + match.group(6).strip()

            options = []
            if 'A)' in options_text or 'A.' in options_text:
                option_matches = re.findall(r'([A-D][.\s)])(.*?)(?=(?:[A-D][.\s)])|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"{opt_letter} {opt_text.strip()}")
            elif '(a)' in options_text or '(a)' in options_text:
                option_matches = re.findall(r'\((a|b|c|d)\)[.\s)](.*?)(?=\([a-d]\)|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"({opt_letter}) {opt_text.strip()}")

            difficulty = "MEDIUM"

            student_answer = ""
            correct_answer = ""

            # Extract student answer
            if len(match.groups()) >= 8 and match.group(7):
                student_answer_match = re.search(r'Student Answer: ([a-d])\)', match.group(7), re.IGNORECASE)
                if student_answer_match:
                    student_answer = student_answer_match.group(1).strip().upper()
                    print(f"Extracted Student Answer for Q{question_num}: {student_answer}")  # Debug print

            # Extract correct answer
            if len(match.groups()) >= 9 and match.group(8):
                correct_answer_match = re.search(r'Correct Answer: ([a-d])\)', match.group(8), re.IGNORECASE)
                if correct_answer_match:
                    correct_answer = correct_answer_match.group(1).strip().upper()
                    print(f"Extracted Correct Answer for Q{question_num}: {correct_answer}")  # Debug print

            mcq = {
                'question_num': question_num,
                'question': question_text,
                'options': "//@ ".join(options),
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'difficulty': difficulty
            }

            mcqs.append(mcq)

    return mcqs
def evaluate_single_pdf(file_path):
    """Evaluate student answers from a single PDF file."""
    extracted_text = extract_text(file_path)
    mcqs = extract_mcqs_from_pdf(extracted_text)

    if not mcqs or (len(mcqs) == 1 and 'error' in mcqs[0]):
        return {"error": "Could not extract MCQs from the PDF. Please check the format."}

    evaluation = {
        "student_answers": [],
        "correct_answers": [],
        "score": {"correct": 0, "total": len(mcqs), "percentage": 0},
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": []
    }

    for mcq in mcqs:
        student_answer = mcq.get('student_answer', '').strip()
        correct_answer = mcq.get('correct_answer', '').strip()

        evaluation["student_answers"].append(
            {"question_num": mcq['question_num'], "selected_option": student_answer, "question": mcq['question']})
        evaluation["correct_answers"].append(
            {"question_num": mcq['question_num'], "correct_option": correct_answer, "question": mcq['question']})

        if student_answer == correct_answer:
            evaluation["score"]["correct"] += 1

    evaluation["score"]["percentage"] = (evaluation["score"]["correct"] / evaluation["score"]["total"]) * 100

    if evaluation["score"]["percentage"] >= 75:
        evaluation["strengths"].append("High performance")
    else:
        evaluation["weaknesses"].append("Needs improvement")

    evaluation["improvement_suggestions"].append("Review incorrect answers and understand the concepts better.")

    return evaluation

def extract_mcqs_from_pdf(text):
    """Extracts existing MCQs from PDF text without changing them."""
    # Regex patterns for different question formats
    patterns = [
        r'(\d+)\.\s+(.*?)(?:\n|\r\n?)(A\)[.\s]+(.*?)(?:\n|\r\n?)B\)[.\s]+(.*?)(?:\n|\r\n?)C\)[.\s]+(.*?)(?:\n|\r\n?)D\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer: [a-d]\)[^\n\r]+)(?:\n|\r\n?)(Correct Answer: [a-d]\)[^\n\r]+)(?=\n\d+\.\s+|\Z)',
        r'(Q\.\s*\d+)\.\s+(.*?)(?:\n|\r\n?)(\(a\)[.\s]+(.*?)(?:\n|\r\n?)\(b\)[.\s]+(.*?)(?:\n|\r\n?)\(c\)[.\s]+(.*?)(?:\n|\r\n?)\(d\)[.\s]+(.*?))(?:\n|\r\n?)(Student Answer: [a-d]\)[^\n\r]+)(?:\n|\r\n?)(Correct Answer: [a-d]\)[^\n\r]+)(?=\n\s*Q\.\s*\d+|$)',
    ]

    mcqs = []

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            question_num = match.group(1).strip()
            question_text = match.group(2).strip()
            options_text = ""

            if len(match.groups()) >= 4:
                options_text = "A) " + match.group(3).strip() + "\nB) " + match.group(
                    4).strip() + "\nC) " + match.group(5).strip() + "\nD) " + match.group(6).strip()

            # Extract individual options
            options = []
            if 'A)' in options_text or 'A.' in options_text:
                option_matches = re.findall(r'([A-D][.\s)])(.*?)(?=(?:[A-D][.\s)])|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"{opt_letter} {opt_text.strip()}")
            elif '(a)' in options_text or '(a)' in options_text:
                option_matches = re.findall(r'\((a|b|c|d)\)[.\s)](.*?)(?=\([a-d]\)|$)', options_text, re.DOTALL)
                for opt_letter, opt_text in option_matches:
                    options.append(f"({opt_letter}) {opt_text.strip()}")

            # Default to medium difficulty if not specified
            difficulty = "MEDIUM"

            # Look for answer key in the document
            student_answer = ""
            correct_answer = ""
            if len(match.groups()) >= 8 and match.group(7):
                student_answer_match = re.search(r'Student Answer: ([a-d])\)', match.group(7))
                if student_answer_match:
                    student_answer = student_answer_match.group(1).strip()

            if len(match.groups()) >= 9 and match.group(8):
                correct_answer_match = re.search(r'Correct Answer: ([a-d])\)', match.group(8))
                if correct_answer_match:
                    correct_answer = correct_answer_match.group(1).strip()
            mcq = {
                'question_num': question_num,
                'question': question_text,
                'options': "//@ ".join(options),
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
    [Options]: Option A Option B Option C Option D
    [Student Answer]: The student answer text here?
    [Correct Answer]: The correct option (A, B, C, or D) if available
    [Difficulty Level]: EASY or MEDIUM or HARD (assign an appropriate difficulty level)

    Important: 
    1. Use //@ as the separator between options.
    2. Keep the original question text and options EXACTLY as they appear in the document.
    3. If answer keys are provided in the document, match them to the questions.
    4. The difficulty level should be one of: EASY, MEDIUM, or HARD based on the complexity of the question.
    5. Keep the original Student Answer text and options EXACTLY as they appear in the document.


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
                elif line.startswith('[Correct Answer]:'):
                    mcq['answer'] = line[line.find(':') + 1:].strip()
                elif line.startswith('[Difficulty Level]:'):
                    mcq['difficulty'] = line[line.find(':') + 1:].strip()

            # Only add if we have required fields
            if 'question' in mcq and 'options' in mcq:
                # Set default values if missing
                if 'question_num' not in mcq:
                    mcq['question_num'] = str(len(mcqs) + 1)
                if 'answer' not in mcq:
                    mcq['answer'] = ""
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