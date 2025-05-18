#app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from mcq_generator import extract_text, generate_mcqs, extract_mcqs_from_pdf, evaluate_single_pdf
import os
from flask_session import Session
import pandas as pd
from datetime import datetime
import io
import json
from mcq_generator import generate_evaluation_pdf

app = Flask(__name__)
app.secret_key = os.urandom(24)  # More secure secret key generation

# Ensure upload and CSV directories exist
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["CSV_FOLDER"] = "csv_files"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["CSV_FOLDER"], exist_ok=True)

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
Session(app)
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


@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    try:
        # Use filesystem-based session storage instead of cookie
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

        # Get the CSV file path
        csv_path = os.path.join(app.config["CSV_FOLDER"], filename)

        # If session data is missing, try to regenerate it from the CSV file
        if 'evaluation' not in session or 'comparison' not in session:
            # Load data from CSV
            df = pd.read_csv(csv_path)

            # Recreate evaluation data structure
            evaluation = {
                "score": {
                    "total": 0,
                    "correct": 0,
                    "percentage": 0
                },
                "specialty_performance": {},
                "strengths": [],
                "weaknesses": [],
                "improvement_suggestions": [],
                "detailed_feedback": ["This is a regenerated report based on CSV data."],
                "upsc_fit_assessment": "Assessment based on CSV data."
            }

            # Find the row with OVERALL SCORE
            overall_row = df[df['Category'] == 'OVERALL SCORE']
            if not overall_row.empty:
                score_parts = overall_row.iloc[0]['Score'].split('/')
                if len(score_parts) == 2:
                    evaluation['score']['correct'] = int(score_parts[0])
                    evaluation['score']['total'] = int(score_parts[1])
                    evaluation['score']['percentage'] = float(overall_row.iloc[0]['Percentage'].strip('%'))

            # Extract specialty performance data
            for idx, row in df.iterrows():
                if row['Category'] != 'OVERALL SCORE':
                    score_parts = row['Score'].split('/')
                    if len(score_parts) == 2:
                        evaluation['specialty_performance'][row['Category']] = {
                            'correct': int(score_parts[0]),
                            'total': int(score_parts[1]),
                            'percentage': float(row['Percentage'].strip('%'))
                        }

            # Create basic comparison data
            comparison = []

            # Add to session
            session['evaluation'] = evaluation
            session['comparison'] = comparison

        # Logo path
        logo_path = os.path.join(os.path.dirname(__file__), 'static','logo', 'iedeologi.jpeg')

        # Generate PDF
        pdf_buffer = generate_evaluation_pdf(
            session['evaluation'],
            session['comparison'],
            filename,
            logo_path
        )

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Evaluation_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

    except Exception as e:
        print(f"Download Route Error: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Unexpected error: {str(e)}')
        return redirect(url_for('evaluate'))
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

            # Use the updated evaluation function
            evaluation = evaluate_single_pdf(file_path)

            if "error" in evaluation:
                flash(evaluation["error"])
                return render_template("evaluation.html", evaluation=None)

            # Create comparison data for the Answer Comparison table
            comparison = []
            for mcq in extract_mcqs_from_pdf(extract_text(file_path)):
                student_answer = mcq.get('student_answer', '').strip()
                correct_answer = mcq.get('correct_answer', '').strip()

                # Get options and format them for display
                options_text = mcq.get('options', '')
                options_list = options_text.split("//@ ") if "//@ " in options_text else [options_text]

                is_correct = student_answer.upper() == correct_answer.upper()
                comparison.append({
                    "question_num": mcq['question_num'],
                    "question": mcq['question'],
                    "options": options_list,
                    "selected_option": student_answer,
                    "correct_option": correct_answer,
                    "is_correct": is_correct
                })

            # Create CSV file
            csv_filename = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = os.path.join(app.config["CSV_FOLDER"], csv_filename)

            # Create a more detailed DataFrame for the CSV
            df_data = []
            for category, perf in evaluation["specialty_performance"].items():
                df_data.append({
                    "Category": category,
                    "Score": f"{perf['correct']}/{perf['total']}",
                    "Percentage": f"{perf['percentage']:.1f}%"
                })

            df = pd.DataFrame(df_data)

            # Add overall score
            df = pd.concat([
                pd.DataFrame([{
                    "Category": "OVERALL SCORE",
                    "Score": f"{evaluation['score']['correct']}/{evaluation['score']['total']}",
                    "Percentage": f"{evaluation['score']['percentage']:.1f}%"
                }]),
                df
            ])

            df.to_csv(csv_path, index=False)
            session.clear()
            # Store data in session for PDF download
            session['evaluation'] = evaluation
            session['comparison'] = comparison
            session['csv_filename'] = csv_filename

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
    app.run(host='0.0.0.0', port=5000, debug=True)