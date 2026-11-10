"""
FAQ Chatbot - web interface
CodeAlpha Artificial Intelligence Internship - Task 2

Serves the chat page and passes each message to the matching engine in
chatbot.py, which returns the best matching FAQ answer.

Run:  python app.py   then open http://127.0.0.1:5001
"""

from flask import Flask, jsonify, render_template, request

from chatbot import FAQBot

app = Flask(__name__)
bot = FAQBot()

MAX_MESSAGE_LENGTH = 300


@app.route("/")
def index():
    return render_template(
        "index.html",
        bot_name=bot.name,
        starters=bot.starter_questions(),
        max_length=MAX_MESSAGE_LENGTH,
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "")[:MAX_MESSAGE_LENGTH]
    return jsonify(bot.reply(message))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
