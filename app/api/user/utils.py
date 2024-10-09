import csv
from bs4 import BeautifulSoup
from docx import Document
import PyPDF2
import json
from datetime import datetime
from app.mongo import get_db
from docx.shared import Pt
from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn
from flask import session
import re

def get_pdf_text(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def get_docx_text(file_path):
    doc = Document(file_path)

    # Extract text from the DOCX file
    full_content = []

    for para in doc.paragraphs:
        if para.text.strip():  # Check if paragraph is not empty
            # Check if the paragraph has any numbering
            if para.style.name.startswith('List'):
                if para.style.name == 'List Number':
                    numbering = 'Number: '  # Define a prefix for numbered lists
                elif para.style.name == 'List Bullet':
                    numbering = 'Bullet: '  # Define a prefix for bulleted lists
                else:
                    numbering = ''  # No numbering
                
                content = f"{numbering}{para.text}" 
            else:
                content = para.text
            full_content.append(content)
    
    return '\n'.join(full_content)

def clean_text(str):
    cite_pattern = r"【\d+†source】|【\d+:\d+†source】|【\d+:\d+†fuente】|【.*?】"
    return re.sub(cite_pattern, "", str)

def get_history(user, title=""):
    db = get_db()
    collection = db["saves"]
    pipeline = []
    if title == "":
        pipeline.append({"$project": {"_id": 1, "user": 1, "modifiedAt": 1}})
        pipeline.append({"$match": {"user": user}})
        pipeline.append({"$sort": {"modifiedAt": -1}})
        pipeline.append({"$limit": 1})
    else:
        pipeline.append(
            {"$project": {"_id": 1, "user": 1, "modifiedAt": 1, "title": 1}}
        )
        pipeline.append({"$match": {"user": user, "title": title}})
    find_data = list(collection.aggregate(pipeline=pipeline))
    if len(find_data) > 1:
        return "Error"
    elif len(find_data) == 1:
        history = collection.find_one({"_id": find_data[0]["_id"]})
        print(history)
        return history
    else:
        return "No data"


def get_current_state(user):
    db = get_db()
    collection = db["current_state"]
    history = collection.find_one({"user": user})
    if history:
        history.pop("_id", None)
        return history
    else:
        collection.insert_one({"user": user})
        return {"user": user}


def update_current_state(user, field, data):
    db = get_db()
    collection = db["current_state"]
    query_filter = {"user": user}
    update_date = {}
    update_date[field] = data
    update_operation = {}
    update_operation["$set"] = update_date
    collection.update_one(query_filter, update_operation)


def get_current_data_field(user, field):
    db = get_db()
    collection = db["current_state"]
    history = collection.find_one({"user": user})
    if field in history:
        return history[field]
    else:
        return ""


def get_settings(field):
    db = get_db()
    collection = db["settings"]
    settings = collection.find_one()
    return settings[field]


def get_title_list(user):
    db = get_db()
    collection = db["results"]
    pipeline = [{"$project": {"title": 1, "user": 1}}, {"$match": {"user": user}}]
    res = list(collection.aggregate(pipeline=pipeline))
    return_data = []
    for each in res:
        return_data.append(each["title"])
    return return_data


def save_text(user, title):
    loading_data = get_current_state(user)
    loading_data["title"] = title
    loading_data["modifiedAt"] = datetime.now()

    # Asegúrate de que las evidencias se guarden correctamente
    evidencias_cumplen = session.get("evidencias_cumplen", [])
    evidencias_no_cumplen = session.get("evidencias_no_cumplen", [])

    loading_data["evidencias_cumplen"] = evidencias_cumplen
    loading_data["evidencias_no_cumplen"] = evidencias_no_cumplen

    db = get_db()
    results = db["results"]
    currents = db["current_state"]

    # Verifica si ya existe un análisis con el mismo título
    pipeline = [
        {"$project": {"_id": 1, "title": 1, "user": 1}},
        {"$match": {"user": user, "title": title}},
    ]
    res = list(results.aggregate(pipeline=pipeline))

    # Si ya existe, lo eliminamos para sobreescribir
    if len(res) > 0:
        results.delete_one({"user": user, "title": title})

    # Insertar los datos en `results`
    results.insert_one(loading_data)

    # También actualizamos el `current_state`
    currents.delete_one({"user": user})
    currents.insert_one(loading_data)

    return {"message": "sucess"}, 200


def set_text(user, title):
    db = get_db()
    results = db["results"]
    currents = db["current_state"]

    # Buscar los datos guardados en `results`
    set_data = results.find_one({"user": user, "title": title})

    # Si los datos se encuentran, los transferimos a `current_state`
    if set_data:
        currents.delete_one({"user": user})
        currents.insert_one(set_data)

        # Asegúrate de que las evidencias también se carguen en la sesión
        session["evidencias_cumplen"] = set_data.get("evidencias_cumplen", [])
        session["evidencias_no_cumplen"] = set_data.get("evidencias_no_cumplen", [])

        return {"message": "sucess"}, 200
    else:
        return {"message": "Análisis no encontrado"}, 404


def reset_current_state(user):
    db = get_db()
    currents = db["current_state"]
    currents.delete_one({"user": user})  # Esto debe borrar el estado anterior

    return
