from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from audio_video_streaming import user_input_thread

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import os
import datetime
import json
import uuid

# === Azure Blob Storage Setup ===
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "logs"

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
semester = os.getenv("semester", "ds100-su25")

def log_to_blob(response_data):
    prod = os.getenv("PRODUCTION", "false").lower() == "true"
    folder = f"{semester}/production" if prod else f"{semester}/test"
    blob_name = f"{folder}/logs.json"

    try:
        # Ensure container exists
        if not container_client.exists():
            blob_service_client.create_container(CONTAINER_NAME)

        blob_client = container_client.get_blob_client(blob_name)

        # Try to read existing logs
        try:
            existing_blob = blob_client.download_blob().readall()
            logs = json.loads(existing_blob)
            if not isinstance(logs, list):
                logs = [logs]
        except ResourceNotFoundError:
            logs = []

        # Append and upload
        logs.append(response_data)
        blob_client.upload_blob(json.dumps(logs, indent=2), overwrite=True)
        print(f"Appended log to: {blob_name}")

    except Exception as e:
        print(f"Failed to upload log to Azure Blob: {e}")

# === Flask App ===
app = Flask(__name__)
CORS(app)

conversation = []

@app.route("/", methods=["GET", "POST"])
def chat():
    global conversation

    # Handle JSON request from extension
    if request.is_json:
        data = request.get_json()
        user_input = data.get("question")
        if user_input:
            response_id = str(uuid.uuid4())
            response = user_input_thread(user_input)
            print(response)

            log_to_blob({
                "log_type": "generation",
                "response_id": response_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "source": "extension",
                "user_input": user_input,
                "gpt_response": response.get("GPT Response", "")
            })

            return jsonify({"response": response.get("GPT Response", ""), "response_id": response_id})
        return jsonify({"response": "No input received."}), 400

    # Handle HTML form POST
    if request.method == "POST":
        user_input = request.form.get("user_input")
        if user_input:
            conversation.append({"user": "You", "text": user_input})
            response = user_input_thread(user_input)
            print(response)
            conversation.append({"user": "Askademia", "text": response.get("GPT Response", "")})

            log_to_blob({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "source": "form",
                "user_input": user_input,
                "gpt_response": response.get("GPT Response", "")
            })

    return render_template("index.html", conversation=conversation)

@app.route("/feedback", methods=["POST"])
def feedback():
    if request.is_json:
        data = request.get_json()
        response_id = data.get("response_id")
        rating = data.get("rating")
        feedback_text = data.get("feedback_text")

        if not response_id:
            return jsonify({"status": "error", "message": "Missing response_id"}), 400

        log_to_blob({
            "log_type": "feedback",
            "response_id": response_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "rating": rating,
            "feedback_text": feedback_text
        })

        return jsonify({"status": "success", "message": "Feedback logged"})
    return jsonify({"status": "error", "message": "Request must be JSON"}), 400


if __name__ == "__main__":
    conversation = []
    app.run(debug=True)