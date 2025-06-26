from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from audio_video_streaming import user_input_thread

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
            response = user_input_thread(user_input)
            print(response)
            return jsonify({"response": response['GPT Response']})
        return jsonify({"response": "No input received."}), 400

    # Handle HTML form POST
    if request.method == "POST":
        user_input = request.form.get("user_input")
        if user_input:
            conversation.append({"user": "You", "text": user_input})
            response = user_input_thread(user_input)
            print(response)
            conversation.append({"user": "Askademia", "text": response['GPT Response']})

    return render_template("index.html", conversation=conversation)

if __name__ == "__main__":
    conversation = []
    app.run(debug=True)
