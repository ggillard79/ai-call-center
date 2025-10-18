from flask import Flask, request, Response
import openai
import os

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/voice", methods=["POST"])
def voice():
    user_input = request.form.get("SpeechResult", "")
    prompt = f"L'utilisateur dit : {user_input}. Réponds comme une réceptionniste polie qui gère les appels pour un salon de coiffure appelé Harmonie."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response['choices'][0]['message']['content']

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="fr-FR">{reply}</Say>
</Response>"""
    return Response(twiml, mimetype='text/xml')

@app.route("/")
def home():
    return "Serveur IA Call Center opérationnel."
