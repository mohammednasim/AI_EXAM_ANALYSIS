from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from mcq_generator import extract_text, generate_mcqs, extract_mcqs_from_pdf, \
    evaluate_single_pdf
import os
import pandas as pd
from datetime import datetime
import io
import json

app = Flask(__name__)
app.secret_key = "mcq_extraction_app_secret_key"  # For flash messages and session

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["CSV_FOLDER"] = "csv_files"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["CSV_FOLDER"], exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/extract", methods=["GET", "POST"])
def extract_mcqs():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)

        uploaded_file = request.files["file"]

        if uploaded_file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if uploaded_file and uploaded_file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file.filename)
            uploaded_file.save(file_path)

            # Extract text from PDF
            extracted_text = extract_text(file_path)

            # Extract existing MCQs from the PDF
            mcqs = extract_mcqs_from_pdf(extracted_text)

            if not mcqs or (len(mcqs) == 1 and 'error' in mcqs[0]):
                flash('Could not extract MCQs from the PDF. Please check the format.')
                return redirect(request.url)

            # Create CSV file with the MCQs
            csv_filename = f"extracted_mcqs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = os.path.join(app.config["CSV_FOLDER"], csv_filename)

            # Create DataFrame for CSV
            df = pd.DataFrame({
                'Question Number': [mcq.get('question_num', '') for mcq in mcqs],
                'Question': [mcq.get('question', '') for mcq in mcqs],
                'Options': [mcq.get('options', '') for mcq in mcqs],
                'Correct Answer': [mcq.get('answer', '') for mcq in mcqs],
                'Difficulty Level': [mcq.get('difficulty', '') for mcq in mcqs]
            })

            # Save to CSV
            df.to_csv(csv_path, index=False)

            # Store in session for download
            session['csv_filename'] = csv_filename

            return render_template("quiz.html", mcqs=mcqs, csv_filename=csv_filename, mode="extract")
        else:
            flash('Please upload a PDF file')
            return redirect(request.url)

    return render_template("extract.html")


@app.route("/generate", methods=["GET", "POST"])
def generate():
    if request.method == "POST":
        uploaded_file = request.files["file"]
        num_questions = int(request.form.get("num_questions", 5))

        if uploaded_file.filename != "":
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file.filename)
            uploaded_file.save(file_path)

            extracted_text = extract_text(file_path)

            # Generate MCQs with difficulty levels
            mcqs = generate_mcqs(extracted_text, num_questions)

            # Create CSV file with the MCQs
            csv_filename = f"generated_mcqs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = os.path.join(app.config["CSV_FOLDER"], csv_filename)

            # Create DataFrame for CSV
            df = pd.DataFrame({
                'Question': [mcq.get('question', '') for mcq in mcqs],
                'Options': [mcq.get('options', '') for mcq in mcqs],
                'Correct Answer': [mcq.get('answer', '') for mcq in mcqs],
                'Difficulty Level': [mcq.get('difficulty', '') for mcq in mcqs]
            })

            # Save to CSV
            df.to_csv(csv_path, index=False)

            return render_template("quiz.html", mcqs=mcqs, csv_filename=csv_filename, mode="generate")

    return render_template("generate.html")


@app.route("/evaluate", methods=["GET", "POST"])
def evaluate():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('Please upload a PDF file')
            return redirect(request.url)

        uploaded_file = request.files["file"]

        if uploaded_file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if uploaded_file and uploaded_file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file.filename)
            uploaded_file.save(file_path)

            extracted_text = extract_text(file_path)
            mcqs = extract_mcqs_from_pdf(extracted_text)

            if not mcqs or (len(mcqs) == 1 and 'error' in mcqs[0]):
                flash('Could not extract MCQs from the PDF. Please check the format.')
                return render_template("evaluation.html", evaluation=None)

            evaluation = {
                "student_answers": [],
                "correct_answers": [],
                "score": {"correct": 0, "total": len(mcqs), "percentage": 0},
                "strengths": [],
                "weaknesses": [],
                "improvement_suggestions": []
            }

            comparison = []

            for mcq in mcqs:
                student_answer = mcq.get('student_answer', '').strip()
                correct_answer = mcq.get('correct_answer', '').strip()

                # Get options and format them for display
                options_text = mcq.get('options', '')
                options_list = options_text.split("//@ ") if "//@ " in options_text else [options_text]

                evaluation["student_answers"].append(
                    {"question_num": mcq['question_num'], "selected_option": student_answer,
                     "question": mcq['question']})
                evaluation["correct_answers"].append(
                    {"question_num": mcq['question_num'], "correct_option": correct_answer,
                     "question": mcq['question']})

                is_correct = student_answer.upper() == correct_answer.upper()
                if is_correct:
                    evaluation["score"]["correct"] += 1

                comparison.append({
                    "question_num": mcq['question_num'],
                    "question": mcq['question'],
                    "options": options_list,  # Add options to the comparison data
                    "selected_option": student_answer,
                    "correct_option": correct_answer,
                    "is_correct": is_correct
                })

            evaluation["score"]["percentage"] = (evaluation["score"]["correct"] / evaluation["score"]["total"]) * 100 if \
            evaluation["score"]["total"] > 0 else 0

            # Generate feedback based on performance
            if evaluation["score"]["percentage"] >= 85:
                evaluation["strengths"].append("Excellent performance! You've answered most questions correctly.")
            elif evaluation["score"]["percentage"] >= 70:
                evaluation["strengths"].append("Good performance! You've answered a majority of questions correctly.")
            elif evaluation["score"]["percentage"] >= 50:
                evaluation["strengths"].append(
                    "Average performance. You've answered about half the questions correctly.")
            else:
                evaluation["weaknesses"].append("Needs improvement. You should review the incorrect answers carefully.")

            evaluation["improvement_suggestions"].append("Review incorrect answers and understand the concepts better.")
            evaluation["improvement_suggestions"].append(
                "Consider studying the topics covered in the incorrect questions more thoroughly.")
            evaluation["improvement_suggestions"].append("Practice similar questions to improve your understanding.")

            # Create CSV file
            csv_filename = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = os.path.join(app.config["CSV_FOLDER"], csv_filename)

            df = pd.DataFrame(comparison)
            df.to_csv(csv_path, index=False)

            return render_template("evaluation.html",
                                   evaluation=evaluation,
                                   csv_filename=csv_filename,
                                   comparison=comparison)
        else:
            flash('Please upload a PDF file')
            return redirect(request.url)

    return render_template("evaluate.html")
@app.route("/download_csv/<filename>")
def download_csv(filename):
    csv_path = os.path.join(app.config["CSV_FOLDER"], filename)
    return send_file(csv_path, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True)