from flask import Flask, request, render_template
from audio_video_streaming import user_input_thread

app = Flask(__name__)

conversation = []

@app.route("/", methods=["GET", "POST"])
def chat():
    global conversation

    if request.method == "POST":
        user_input = request.form.get("user_input")
        if user_input:
            conversation.append({"user": "You", "text": user_input})

            response = user_input_thread(user_input)

            conversation.append({"user": "Askademia", "text": response['GPT Response']})

    return render_template("index.html", conversation=conversation)


if __name__ == "__main__":
    conversation = []
    app.run(debug=True)
