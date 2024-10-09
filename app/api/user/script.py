from openai import OpenAI
from .utils import clean_text
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

client = OpenAI(api_key=OPENAI_KEY)

def upload(file_path):

    message_file = client.files.create(
        file=open(file_path, "rb"), purpose="assistants"
    )

    return message_file.id

def openAI_response(send_message, file_id=""):
    max_files = 10
    all_responses = []

    # Verificar si file_id es una lista de archivos válida
    if not isinstance(file_id, list):
        file_id = [file_id]

    # Crear un thread sin archivos adjuntos si file_id está vacío
    if not file_id or file_id == [""]:
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": send_message,
                }
            ]
        )
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=ASSISTANT_ID
        )

        messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
        message_content = messages[0].content[0].text
        output = message_content.value
        output = clean_text(output)
        all_responses.append(output)

    else:
        # Procesar archivos en lotes de 10
        file_batches = [file_id[i:i + max_files] for i in range(0, len(file_id), max_files)]

        for batch in file_batches:
            # Verificar que cada ID de archivo en el batch es una cadena válida
            batch = [file for file in batch if isinstance(file, str) and file]

            if not batch:
                continue

            # Adjuntar archivos al mensaje
            attach = [{"file_id": each, "tools": [{"type": "file_search"}]} for each in batch]

            # Crear thread con archivos adjuntos
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": send_message,
                        "attachments": attach,  # Adjuntar archivos
                    }
                ]
            )

            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id, assistant_id=ASSISTANT_ID
            )

            # Obtener los mensajes de respuesta
            messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
            message_content = messages[0].content[0].text
            output = message_content.value
            output = clean_text(output)
            all_responses.append(output)

            # Borrar el thread para liberar recursos
            client.beta.threads.delete(thread.id)

    # Concatenar todas las respuestas y devolverlas
    return " ".join(all_responses)


    