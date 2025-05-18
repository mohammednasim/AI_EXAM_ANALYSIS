#mcq_generator.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
import PyPDF2
import re
import io
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import PageBreak
import numpy as np
import matplotlib
from datetime import datetime
import io
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Set this before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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


import json  # Add this import at the top of the file

def ai_detailed_evaluation(mcqs, evaluation):
    """
    Use AI to provide detailed, nuanced evaluation of student performance
    based on extracted MCQs and initial evaluation.
    """
    model = genai.GenerativeModel("gemini-1.5-pro")

    # Prepare a comprehensive prompt for detailed analysis
    prompt = f"""
    Perform a comprehensive, academic-level analysis of the student's multiple-choice question (MCQ) performance with the following details:

    Performance Overview:
    - Total Questions: {evaluation['score']['total']}
    - Correct Answers: {evaluation['score']['correct']}
    - Overall Percentage: {evaluation['score']['percentage']:.2f}%

    Categories Performance:
    {json.dumps(evaluation['specialty_performance'], indent=2)}

    Existing Strengths: {', '.join(evaluation['strengths'])}
    Existing Weaknesses: {', '.join(evaluation['weaknesses'])}

    Provide a comprehensive and professional evaluation including:
    1. Detailed Feedback: An in-depth analysis of performance
    2. Areas for Improvement: Specific subject areas needing attention
    3. Targeted Improvement Suggestions: Actionable recommendations
    4. UPSC Exam Readiness Assessment: Detailed insights into preparation level
    5. Strategic Learning Recommendations: Personalized study approach

    Response Format:
    [Detailed Feedback]: Comprehensive performance overview
    [Areas for Improvement]: Specific weakness analysis
    [Improvement Suggestions]: Actionable, targeted recommendations
    [UPSC Exam Readiness]: Precise assessment and strategy
    [Learning Strategy]: Personalized study plan recommendations

    Be nuanced, professional, and provide constructive, actionable insights.
    """

    try:
        response = model.generate_content(prompt)
        ai_evaluation = response.text.strip()

        # Parse AI's response into structured sections
        sections = {
            'detailed_feedback': re.search(r'\[Detailed Feedback\]:(.*?)(?=\[Areas|$)', ai_evaluation, re.DOTALL),
            'areas_for_improvement': re.search(r'\[Areas for Improvement\]:(.*?)(?=\[Improvement|$)', ai_evaluation,
                                               re.DOTALL),
            'improvement_suggestions': re.search(r'\[Improvement Suggestions\]:(.*?)(?=\[UPSC|$)', ai_evaluation,
                                                 re.DOTALL),
            'upsc_readiness': re.search(r'\[UPSC Exam Readiness\]:(.*?)(?=\[Learning|$)', ai_evaluation, re.DOTALL),
            'learning_strategy': re.search(r'\[Learning Strategy\]:(.*?)$', ai_evaluation, re.DOTALL)
        }

        # Update evaluation with AI-generated insights
        if sections['detailed_feedback']:
            evaluation['detailed_feedback'] = [
                feedback.strip()
                for feedback in sections['detailed_feedback'].group(1).strip().split('\n')
                if feedback.strip()
            ]
        else:
            evaluation['detailed_feedback'] = ["Comprehensive performance analysis not available."]

        if sections['areas_for_improvement']:
            evaluation['weaknesses'] = [
                weakness.strip()
                for weakness in sections['areas_for_improvement'].group(1).strip().split('\n')
                if weakness.strip()
            ]

        if sections['improvement_suggestions']:
            evaluation['improvement_suggestions'] = [
                suggestion.strip()
                for suggestion in sections['improvement_suggestions'].group(1).strip().split('\n')
                if suggestion.strip()
            ]

        if sections['upsc_readiness']:
            evaluation['upsc_fit_assessment'] = sections['upsc_readiness'].group(1).strip()

        if sections['learning_strategy']:
            evaluation['learning_strategy'] = [
                strategy.strip()
                for strategy in sections['learning_strategy'].group(1).strip().split('\n')
                if strategy.strip()
            ]

        return evaluation

    except Exception as e:
        print(f"Error in AI-driven evaluation: {e}")
        # Fallback to existing evaluation if AI analysis fails
        return evaluation
def evaluate_single_pdf(file_path):
    """Enhanced evaluation method incorporating AI-driven detailed analysis."""
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

    # Determine question category and process each MCQ
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

    # Existing logic for strengths, weaknesses, etc. (kept the same as before)
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
        evaluation["upsc_fit_assessment"] = "Based on your performance, you show good potential for the UPSC examination. Your overall score indicates a strong foundation in the tested subjects."
    elif evaluation["score"]["percentage"] >= 60:
        evaluation["upsc_fit_assessment"] = "You show moderate potential for the UPSC examination. With focused preparation in your weaker areas, you can improve your chances significantly."
    else:
        evaluation["upsc_fit_assessment"] = "Your current performance suggests you need substantial preparation before attempting the UPSC examination. Focus on building a stronger foundation in all subjects, particularly in your weaker areas."

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

    # Add AI-driven detailed evaluation
    evaluation = ai_detailed_evaluation(mcqs, evaluation)

    return evaluation

import re


# In mcq_generator.py, update the extract_mcqs_from_pdf function:

# Update the extract_mcqs_from_pdf function in mcq_generator.py:

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


import io
import os
from datetime import datetime
import numpy as np
import matplotlib

matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


# Helper functions
def get_grade(percentage):
    """Return a letter grade based on percentage"""
    if percentage >= 90:
        return "A+ (Outstanding)"
    elif percentage >= 80:
        return "A (Excellent)"
    elif percentage >= 70:
        return "B+ (Very Good)"
    elif percentage >= 60:
        return "B (Good)"
    elif percentage >= 50:
        return "C (Average)"
    elif percentage >= 40:
        return "D (Below Average)"
    else:
        return "F (Needs Improvement)"


def get_grade_color(percentage):
    """Return color for grade row"""
    if percentage >= 80:
        return colors.green
    elif percentage >= 60:
        return colors.lightgreen
    elif percentage >= 40:
        return colors.orange
    else:
        return colors.red


def get_performance_status(percentage):
    """Return status text based on percentage"""
    if percentage >= 80:
        return "Excellent"
    elif percentage >= 70:
        return "Good"
    elif percentage >= 60:
        return "Satisfactory"
    elif percentage >= 40:
        return "Needs Improvement"
    else:
        return "Critical Attention Required"


def get_performance_color(percentage):
    """Return color for performance status"""
    if percentage >= 80:
        return colors.green
    elif percentage >= 70:
        return colors.lightgreen
    elif percentage >= 60:
        return colors.limegreen
    elif percentage >= 40:
        return colors.orange
    else:
        return colors.red


def get_readiness_level(percentage):
    """Return UPSC readiness level"""
    if percentage >= 85:
        return "Advanced"
    elif percentage >= 70:
        return "Proficient"
    elif percentage >= 50:
        return "Developing"
    else:
        return "Beginner"


def get_readiness_description(level):
    """Return description for readiness level"""
    descriptions = {
        "Advanced": "Ready for the UPSC exam with final refinements needed",
        "Proficient": "Good preparation level, needs targeted improvements",
        "Developing": "Reasonable foundation, but requires significant improvement",
        "Beginner": "Fundamental concepts need reinforcement before exam readiness"
    }
    return descriptions.get(level, "Assessment not available")


def get_strongest_subject(specialty_performance):
    """Return the strongest subject"""
    if not specialty_performance:
        return "Not available"
    strongest = max(specialty_performance.items(), key=lambda x: x[1]['percentage'])
    return strongest[0]


def get_weakest_subject(specialty_performance):
    """Return the weakest subject"""
    if not specialty_performance:
        return "Not available"
    weakest = min(specialty_performance.items(), key=lambda x: x[1]['percentage'])
    return weakest[0]


def get_performance_text(percentage):
    """Return descriptive text for performance"""
    if percentage >= 85:
        return "excellent command of the subject matter"
    elif percentage >= 70:
        return "good understanding with some areas for improvement"
    elif percentage >= 60:
        return "adequate grasp of core concepts but needs strengthening"
    elif percentage >= 50:
        return "basic understanding with significant areas needing improvement"
    else:
        return "fundamental gaps that require immediate attention"


def generate_evaluation_pdf(evaluation, comparison, csv_filename, logo_path=None):
    """
    Generate a comprehensive PDF report of the student's evaluation with enhanced feedback
    and personalized improvement plan spanning multiple pages.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Enhanced Title Style
    title_style = styles['Title']
    title_style.alignment = 1  # Center alignment

    # Custom styles
    heading1_style = styles['Heading1']
    heading1_style.alignment = 1
    heading1_style.fontSize = 16

    heading2_style = styles['Heading2']
    heading2_style.fontSize = 14
    heading2_style.spaceAfter = 10

    normal_style = styles['Normal']
    normal_style.spaceAfter = 6

    bullet_style = styles['Normal']
    bullet_style.leftIndent = 20
    bullet_style.spaceAfter = 3

    # Add Logo
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=2 * inch, height=1 * inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"Logo loading error: {e}")

    # Title and Date
    elements.append(Paragraph("COMPREHENSIVE EVALUATION REPORT", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles['Italic']))
    elements.append(Spacer(1, 20))

    # Performance Overview Pie Chart
    plt.figure(figsize=(6, 4))
    labels = ['Correct', 'Incorrect']
    sizes = [
        evaluation['score']['correct'],
        evaluation['score']['total'] - evaluation['score']['correct']
    ]
    colors_pie = ['#2ecc71', '#e74c3c']
    plt.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
    plt.title('Performance Overview')
    plt.axis('equal')

    # Save pie chart
    pie_buffer = io.BytesIO()
    plt.savefig(pie_buffer, format='png')
    pie_buffer.seek(0)
    plt.close()

    # Add Pie Chart
    pie_chart = Image(pie_buffer, width=5 * inch, height=4 * inch)
    pie_chart.hAlign = 'CENTER'
    elements.append(pie_chart)
    elements.append(Spacer(1, 12))

    # Performance Summary Table with improved styling
    summary_data = [
        ['PERFORMANCE METRICS', 'VALUE'],
        ['Total Questions', str(evaluation['score']['total'])],
        ['Correct Answers', str(evaluation['score']['correct'])],
        ['Overall Percentage', f"{evaluation['score']['percentage']:.2f}%"],
        ['Overall Grade', get_grade(evaluation['score']['percentage'])]
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Make grade row bold
        ('BACKGROUND', (0, -1), (-1, -1), get_grade_color(evaluation['score']['percentage']))  # Color code grade row
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Category Performance - Bar Chart
    if evaluation['specialty_performance']:
        plt.figure(figsize=(7, 5))
        categories = list(evaluation['specialty_performance'].keys())
        percentages = [perf['percentage'] for perf in evaluation['specialty_performance'].values()]

        # Create horizontal bar chart
        bars = plt.barh(categories, percentages, color=['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6'])
        plt.xlabel('Percentage Correct')
        plt.title('Performance by Category')
        plt.xlim(0, 100)

        # Add percentage on bars
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 1, bar.get_y() + bar.get_height() / 2, f'{width:.1f}%',
                     ha='left', va='center', fontweight='bold')

        # Save bar chart
        bar_buffer = io.BytesIO()
        plt.savefig(bar_buffer, format='png')
        bar_buffer.seek(0)
        plt.close()

        # Add Bar Chart
        elements.append(Paragraph("CATEGORY PERFORMANCE ANALYSIS", heading1_style))
        bar_chart = Image(bar_buffer, width=7 * inch, height=5 * inch)
        bar_chart.hAlign = 'CENTER'
        elements.append(bar_chart)
        elements.append(Spacer(1, 12))

    # Create Performance Radar Chart (if multiple categories)
    if len(evaluation['specialty_performance']) >= 3:
        # Create radar chart data
        categories = list(evaluation['specialty_performance'].keys())
        percentages = [perf['percentage'] for perf in evaluation['specialty_performance'].values()]

        # Add the first value again to close the polygon
        categories.append(categories[0])
        percentages.append(percentages[0])

        # Create radar chart
        plt.figure(figsize=(6, 6))
        ax = plt.subplot(111, polar=True)

        # Convert percentages to radians and plot
        theta = np.linspace(0, 2 * np.pi, len(categories))
        ax.plot(theta, percentages, 'o-', linewidth=2, color='#3498db')
        ax.fill(theta, percentages, alpha=0.25, color='#3498db')

        # Set category labels
        ax.set_xticks(theta[:-1])  # Exclude the last duplicated label
        ax.set_xticklabels(categories[:-1])

        # Set radial limits
        ax.set_ylim(0, 100)
        plt.title('Knowledge Radar Chart')

        # Save radar chart
        radar_buffer = io.BytesIO()
        plt.savefig(radar_buffer, format='png')
        radar_buffer.seek(0)
        plt.close()

        # Add Radar Chart
        radar_chart = Image(radar_buffer, width=5 * inch, height=5 * inch)
        radar_chart.hAlign = 'CENTER'
        elements.append(radar_chart)

    # Page break before detailed analysis
    elements.append(PageBreak())

    # Page 2 - Detailed Analysis Section
    elements.append(Paragraph("DETAILED PERFORMANCE ANALYSIS", heading1_style))
    elements.append(Spacer(1, 12))

    # Strengths and Weaknesses by Topic - Enhanced Table
    elements.append(Paragraph("Subject-wise Performance Breakdown", heading2_style))

    # Create table for category performance
    category_data = [['Subject Area', 'Score', 'Percentage', 'Status']]

    for category, perf in evaluation['specialty_performance'].items():
        status = get_performance_status(perf['percentage'])
        category_data.append([
            category,
            f"{perf['correct']}/{perf['total']}",
            f"{perf['percentage']:.1f}%",
            status
        ])

    category_table = Table(category_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1.5 * inch])
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Add row-specific styling based on performance
    for i, row in enumerate(category_data[1:], 1):
        percentage = float(row[2].strip('%'))
        color = get_performance_color(percentage)
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (3, i), (3, i), color),
            ('TEXTCOLOR', (3, i), (3, i), colors.white if percentage < 60 else colors.black)
        ]))

    elements.append(category_table)
    elements.append(Spacer(1, 20))

    # Detailed Feedback Section
    elements.append(Paragraph("KEY INSIGHTS & RECOMMENDATIONS", heading2_style))

    if evaluation.get('detailed_feedback'):
        for feedback in evaluation['detailed_feedback']:
            cleaned_feedback = feedback.replace("**", "").replace("*", "")
            elements.append(Paragraph(cleaned_feedback, normal_style))

    elements.append(Spacer(1, 15))

    # Areas for Improvement with icons
    elements.append(Paragraph("IMPROVEMENT AREAS", heading2_style))
    for weakness in evaluation.get('weaknesses', []):
        cleaned_weakness = weakness.replace("**", "").replace("*", "")
        elements.append(Paragraph(f"• {cleaned_weakness}", bullet_style))

    elements.append(Spacer(1, 15))

    # Enhanced Improvement Suggestions
    elements.append(Paragraph("ACTIONABLE IMPROVEMENT STRATEGIES", heading2_style))
    for suggestion in evaluation.get('improvement_suggestions', []):
        cleaned_suggestion = suggestion.replace("**", "").replace("*", "")
        elements.append(Paragraph(f"→ {cleaned_suggestion}", bullet_style))

    elements.append(Spacer(1, 15))

    # UPSC Readiness Enhanced Section
    elements.append(Paragraph("UPSC EXAM READINESS ASSESSMENT", heading2_style))

    # Add readiness level indicator
    readiness_level = get_readiness_level(evaluation['score']['percentage'])
    readiness_colors = {
        'Beginner': colors.red,
        'Developing': colors.orange,
        'Proficient': colors.green,
        'Advanced': colors.darkgreen
    }

    readiness_data = [
        ['Readiness Level', 'Description'],
        [readiness_level, get_readiness_description(readiness_level)]
    ]

    readiness_table = Table(readiness_data, colWidths=[2 * inch, 4 * inch])
    readiness_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (0, 1), readiness_colors.get(readiness_level, colors.grey)),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(readiness_table)
    elements.append(Spacer(1, 10))

    cleaned_upsc_assessment = evaluation.get('upsc_fit_assessment', 'No assessment available').replace("**",
                                                                                                       "").replace("*",
                                                                                                                   "")
    elements.append(Paragraph(cleaned_upsc_assessment, normal_style))
    elements.append(Spacer(1, 15))

    # Learning Strategy - Enhanced
    if evaluation.get('learning_strategy'):
        elements.append(Paragraph("PERSONALIZED 30-DAY STUDY PLAN", heading2_style))
        elements.append(
            Paragraph("Based on your performance, we recommend the following focused study plan:", normal_style))

        # Create a table for the study plan
        study_plan_data = [['Week', 'Focus Areas', 'Recommended Activities']]

        # Generate week-by-week plan based on weaknesses
        weaknesses = sorted(
            evaluation['specialty_performance'].items(),
            key=lambda x: x[1]['percentage']
        )

        # Week 1-2: Focus on weakest subjects
        weak_subjects = [w[0] for w in weaknesses if w[1]['percentage'] < 60][:2]
        if weak_subjects:
            week1_subjects = " & ".join(weak_subjects)
            study_plan_data.append([
                "Week 1-2",
                week1_subjects,
                "• Daily 2-hour focused study\n• Practice 20 MCQs daily\n• Review core concepts"
            ])

        # Week 3: Focus on medium subjects
        medium_subjects = [w[0] for w in weaknesses if 60 <= w[1]['percentage'] < 80][:2]
        if medium_subjects:
            week3_subjects = " & ".join(medium_subjects)
            study_plan_data.append([
                "Week 3",
                week3_subjects,
                "• Strengthen understanding\n• Practice previous year questions\n• Enhance answer writing"
            ])

        # Week 4: Revision and mock tests
        study_plan_data.append([
            "Week 4",
            "Comprehensive Revision",
            "• Full-length mock tests\n• Revision of weak areas\n• Timed practice sessions"
        ])

        study_plan_table = Table(study_plan_data, colWidths=[1 * inch, 2 * inch, 3 * inch])
        study_plan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey)
        ]))

        elements.append(study_plan_table)
        elements.append(Spacer(1, 15))

        # Add detailed strategy points
        for strategy in evaluation['learning_strategy']:
            cleaned_strategy = strategy.replace("**", "").replace("*", "")
            elements.append(Paragraph(f"• {cleaned_strategy}", bullet_style))

    # Page break before final summary
    elements.append(PageBreak())

    # Page 3 - Overall Performance Summary and Next Steps
    elements.append(Paragraph("OVERALL PERFORMANCE SUMMARY", heading1_style))
    elements.append(Spacer(1, 12))

    # Performance Summary
    performance_summary = f"""
    Based on your overall score of {evaluation['score']['percentage']:.1f}%, your performance shows 
    {get_performance_text(evaluation['score']['percentage'])}. Your strongest subject is 
    {get_strongest_subject(evaluation['specialty_performance'])} and your area needing most improvement is 
    {get_weakest_subject(evaluation['specialty_performance'])}.
    """

    elements.append(Paragraph(performance_summary, normal_style))
    elements.append(Spacer(1, 15))

    # Next Steps Box
    next_steps_data = [
        ['RECOMMENDED NEXT STEPS'],
        ["""1. Review all incorrect answers and understand the concepts behind them.

2. Focus your study on the weakest subjects identified in this report.

3. Take practice tests regularly to monitor improvement.

4. Schedule a follow-up assessment in 30 days to measure progress.

5. Consider joining our focused group study sessions for your weak areas."""]
    ]

    next_steps_table = Table(next_steps_data, colWidths=[6 * inch])
    next_steps_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 1), (0, 1), 12),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightgrey),
        ('BOX', (0, 0), (0, 1), 2, colors.black),
    ]))

    elements.append(next_steps_table)
    elements.append(Spacer(1, 20))

    # Success Mindset Tips
    elements.append(Paragraph("SUCCESS MINDSET STRATEGIES", heading2_style))

    success_tips = [
        "Embrace challenges as opportunities for growth and learning.",
        "Practice consistent daily study rather than cramming sessions.",
        "Use the Pomodoro technique: 25 minutes of focused study followed by a 5-minute break.",
        "Create mind maps to connect concepts and improve retention.",
        "Teach concepts to others to deepen your understanding.",
        "Focus on understanding rather than memorization.",
        "Take care of your physical health - proper sleep and exercise improve cognitive function."
    ]

    for tip in success_tips:
        elements.append(Paragraph(f"• {tip}", bullet_style))

    elements.append(Spacer(1, 20))

    # Concluding message
    conclusion = f"""
    This report is generated using advanced AI analysis to provide you with personalized insights and recommendations.
    Your dedication to improvement is the key to success in the UPSC examination.

    We wish you the very best in your preparation journey!
    """

    elements.append(Paragraph(conclusion, normal_style))

    # Footer with date and report ID
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        footer_text = f"Report ID: {csv_filename} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Page {canvas.getPageNumber()}"
        canvas.drawCentredString(letter[0] / 2, 20, footer_text)
        canvas.restoreState()

    # Build PDF with footer
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer