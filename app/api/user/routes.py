from flask import (
    jsonify,
    request,
    send_file,
    send_from_directory,
    abort,
    session,
    redirect,
    url_for,
    flash,
)
from datetime import datetime
import time
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import re
from app.mongo import get_db

from . import user_api_bp
from .script import openAI_response
from .utils import (
    get_pdf_text,
    get_current_state,
    update_current_state,
    get_current_data_field,
    get_title_list,
    save_text,
    set_text,
    reset_current_state,
)
from .models import get_users

load_dotenv()
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
STAY_TIME = int(os.getenv("STAY_TIME"))
file_path = ""
pdf_content = ""
analysis_start_time = time.time() - STAY_TIME


def check_login_user():
    if "user_info" not in session:
        flash("We need you to log in to proceed.", "warning")
        return True
    return False


@user_api_bp.route("/pdf/<path:filename>")
def pdf_serve_static(filename):
    if check_login_user():
        return jsonify("no user"), 401
    if ".." in filename or filename.startswith("/"):
        return abort(400)

    uploads_dir = "uploads"
    safe_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.isfile(safe_path):
        return send_from_directory(uploads_dir, filename)
    else:
        return abort(404)

@user_api_bp.route("/reset", methods=["POST"])
def reset():
    if check_login_user():
        return jsonify("no user"), 401
    if request.method == "POST":
        user = session["user_info"]
        reset_current_state(user)

        response = {"message": "Reset done"}
        return jsonify(response), 200


@user_api_bp.route("/uploadfile", methods=["POST"])
def uploadfile():
    if check_login_user():
        return jsonify("no user"), 401
    if request.method == "POST":
        user = session["user_info"]
        if "pdf_file" not in request.files:
            return jsonify("no file"), 400
        file = request.files["pdf_file"]
        if file.filename == "":
            return jsonify("no file name"), 400

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        now = datetime.now()

        formatted_datetime = now.strftime("%y%m%d%H%M%S")

        filename = formatted_datetime + secure_filename(file.filename)
        update_current_state(user, "file_name", filename)

        global file_path
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(file_path)
        update_current_state(user, "file_path", file_path)

        global file_name
        file_name = filename

        global pdf_content
        pdf_content = get_pdf_text(file_path)
        update_current_state(user, "pdf_content", pdf_content)

        result_message = {"file_path": file_name}
        response = {"message": result_message}

        return jsonify(response), 200

@user_api_bp.route("/analysis_pdf", methods=["POST"])
def analysis_pdf():
    if check_login_user():
        return jsonify("no user"), 401
    if request.method == "POST":
        user = session["user_info"]

        # Tiempo de espera antes del análisis, si es necesario
        global analysis_start_time
        during_time = time.time() - analysis_start_time
        if during_time < STAY_TIME:
            time.sleep(STAY_TIME - during_time)

        # Obtener el contenido PDF desde el estado del usuario
        pdf_content = get_current_data_field(user, "pdf_content")
        if not pdf_content:
            return jsonify({"error": "No se encontró el contenido del PDF"}), 400

        # print(f"Contenido del PDF procesado: {pdf_content}")

        # Crear el mensaje para OpenAI solicitando los datos dinámicos
        send_message = f"""
        Below is the content of a legal document. Please extract the following information:

        1. **Document Summary**: Make a brief summary of the following document. The summary should include the main facts, key phrases, and the main context identified in the document. Make sure to highlight the most relevant words and phrases, as well as the context of the topic addressed.
        2. **Fundamental Rights Invoked**: List all the fundamental rights that are mentioned or invoked in the document. **Do not include references to additional articles or texts**, only the right itself. For example: "Fundamental right to a dignified life", "Fundamental right to health".
        3. **Relevant Facts**: Summarize the main facts that are mentioned in the document.
        4. **Petitions**: List the requests or applications that are presented in the document.
        5. **Attached Evidence**: List the attached evidence or documents that are mentioned to support the requests or facts.
        6. **Judgments**: List the judgments that appear in the document, including those that are presented in the following formats:
        - Judgments such as 'Judgment T-444/99', 'SU-509/01', 'C-014/00', etc.
        - Judgments with a format that includes the year, such as 'Judgment T-165 of 1995', 'Judgment T-645 of 1996', 'Judgment T-304 of 1998', 'Judgment T-395 of 1998', among others.
        Make sure to correctly identify both the abbreviated judgments and those that include the year in the form 'of 1995' or similar. Also add a short description of each one if possible. **If no judgments are mentioned in the document, simply indicate that there are no judgments.**

        This is the content of the document: {pdf_content}
        """

        # Llamada a OpenAI para procesar el contenido del PDF
        result_message = openAI_response(send_message)

        if not result_message:
            return jsonify({"error": "Error en la respuesta de OpenAI"}), 500

        # Actualizar el estado del usuario con el resumen del documento
        update_current_state(user, "pdf_resume", result_message)

        # Preparar la respuesta para enviar al frontend
        response = {"message": result_message}

        # Actualizar el tiempo de análisis
        analysis_start_time = time.time()

        return jsonify(response), 200

@user_api_bp.route("/get/state", methods=["POST"])
def history_get():
    if check_login_user():
        return jsonify("no user"), 401
    current_user = session["user_info"]

    # Cargar el historial actual del estado del usuario
    loading_data = get_current_state(current_user)

    return jsonify(loading_data), 200


@user_api_bp.route("/get/list", methods=["POST"])
def list_get():
    if check_login_user():
        return jsonify("no user"), 401
    current_user = session["user_info"]
    title_list = get_title_list(current_user)

    # result_data = get_users()

    return jsonify(title_list), 200


@user_api_bp.route("/save/state", methods=["POST"])
def save_state():
    if check_login_user():
        return jsonify("no user"), 401
    if request.method == "POST":
        try:
            data = request.get_json()
            title = data.get("title")
        except Exception as e:
            return (
                jsonify({"message": "Error procesando los datos.", "error": str(e)}),
                500,
            )

        current_user = session["user_info"]

        # Extraer las evidencias cumple/no cumple desde la sesión
        evidencias_cumplen = session.get("evidencias_cumplen", [])
        evidencias_no_cumplen = session.get("evidencias_no_cumplen", [])

        # Guardar el estado, incluyendo las evidencias
        message, code = save_text(
            current_user, title, evidencias_cumplen, evidencias_no_cumplen
        )
        return jsonify(message), code


@user_api_bp.route("/set/state", methods=["POST"])
def set_state():
    if check_login_user():
        return jsonify("no user"), 401
    if request.method == "POST":
        try:
            data = request.get_json()
            title = data.get("title")
        except Exception as e:
            return (
                jsonify({"message": "Error procesando los datos.", "error": str(e)}),
                500,
            )

        current_user = session["user_info"]

        # Setear el estado del usuario basado en el título seleccionado
        message, code = set_text(current_user, title)
        return jsonify(message), code
