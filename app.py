import os
import time
import uuid
import markdown as markdown_lib
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from utils.document_loader import load_and_chunk_document, SUPPORTED_EXTENSIONS
from agents.crew import run_pipeline, parse_quiz_json, answer_question, MODEL_OPTIONS, DEFAULT_MODEL

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this-later"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DOCUMENTS = {}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in SUPPORTED_EXTENSIONS
    )


def render_markdown(text):
    if not text:
        return ""
    return markdown_lib.markdown(text)


@app.route("/")
def index():
    return render_template("index.html", model_options=MODEL_OPTIONS, default_model=DEFAULT_MODEL)


@app.route("/process", methods=["POST"])
def process():
    uploaded_file = request.files.get("pdf_file")

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please choose a file to upload.")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        allowed_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        flash(f"Unsupported file type. Supported types: {allowed_list}")
        return redirect(url_for("index"))

    include_notes = "notes" in request.form
    include_quiz = "quiz" in request.form
    include_revision = "revision" in request.form
    model_choice = request.form.get("model_choice", DEFAULT_MODEL)

    if not (include_notes or include_quiz or include_revision):
        flash("Please select at least one output to generate.")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded_file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    uploaded_file.save(filepath)

    try:
        chunks = load_and_chunk_document(filepath)
    except ValueError as error:
        flash(str(error))
        return redirect(url_for("index"))
    except Exception as error:
        print(f"Document loading error: {error}")
        flash(
            "Sorry, this file couldn't be read. It may be corrupted. "
            "Please try a different file."
        )
        return redirect(url_for("index"))

    full_text = "\n\n".join(chunk.page_content for chunk in chunks)

    document_id = str(uuid.uuid4())
    DOCUMENTS[document_id] = full_text

    try:
        start_time = time.time()
        results = run_pipeline(
            full_text,
            include_notes=include_notes,
            include_quiz=include_quiz,
            include_revision=include_revision,
            model_key=model_choice,
        )
        elapsed_seconds = round(time.time() - start_time, 1)
    except Exception as error:
        print(f"Agent processing error: {error}")
        flash(f"Something went wrong while generating your results: {error}")
        return redirect(url_for("index"))

    notes_output = results["notes_output"]
    quiz_output = results["quiz_output"]
    revision_output = results["revision_output"]

    quiz_questions = None
    quiz_parse_failed = False
    if quiz_output:
        quiz_questions = parse_quiz_json(quiz_output)
        if quiz_questions is None:
            quiz_parse_failed = True

    return render_template(
        "results.html",
        filename=filename,
        elapsed_seconds=elapsed_seconds,
        document_id=document_id,
        show_notes=include_notes,
        show_quiz=include_quiz,
        show_revision=include_revision,
        notes_html=render_markdown(notes_output),
        revision_html=render_markdown(revision_output),
        quiz_questions=quiz_questions,
        quiz_parse_failed=quiz_parse_failed,
        quiz_raw_output=quiz_output if quiz_parse_failed else None,
    )


@app.route("/ask-upload", methods=["POST"])
def ask_upload():
    uploaded_file = request.files.get("qa_file")

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please choose a file to upload.")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        allowed_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        flash(f"Unsupported file type. Supported types: {allowed_list}")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded_file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    uploaded_file.save(filepath)

    try:
        chunks = load_and_chunk_document(filepath)
    except ValueError as error:
        flash(str(error))
        return redirect(url_for("index"))
    except Exception as error:
        print(f"Document loading error: {error}")
        flash("Sorry, this file couldn't be read. Please try a different file.")
        return redirect(url_for("index"))

    full_text = "\n\n".join(chunk.page_content for chunk in chunks)
    document_id = str(uuid.uuid4())
    DOCUMENTS[document_id] = full_text

    return render_template(
        "ask.html",
        filename=filename,
        document_id=document_id,
        model_options=MODEL_OPTIONS,
        default_model=DEFAULT_MODEL,
    )


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    document_id = data.get("document_id")
    question = data.get("question", "").strip()
    model_choice = data.get("model_choice", DEFAULT_MODEL)

    if not document_id or document_id not in DOCUMENTS:
        return jsonify({"error": "Document not found. Please upload it again."}), 400

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    try:
        answer = answer_question(DOCUMENTS[document_id], question, model_key=model_choice)
    except Exception as error:
        print(f"Q&A error: {error}")
        return jsonify({"error": "Something went wrong answering that question."}), 500

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
