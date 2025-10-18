from flask import Flask, request, Response
import openai
import os

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/voice", methods=["POST"])
def voice():
    try:
        user_input = request.form.get("SpeechResult", "")
        prompt = f"L'utilisateur dit : {user_input}. Réponds comme une réceptionniste polie qui gère les appels pour un salon de coiffure appelé Harmonie."

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Plus fiable que GPT-4 pour le test
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response['choices'][0]['message']['content']

twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/voice" method="POST" timeout="5">
        <Say voice="alice" language="fr-FR">{reply}</Say>
    </Gather>
    <Say voice="alice" language="fr-FR">Je n'ai pas compris. Vous pouvez rappeler plus tard.</Say>
</Response>"""

        return Response(twiml, mimetype='text/xml')

    except Exception as e:
        # Log l'erreur dans les logs Render
        print("🔥 ERREUR GPT :", str(e))
        fallback = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="fr-FR">Désolé, une erreur est survenue avec l'intelligence artificielle.</Say>
</Response>"""
        return Response(fallback, mimetype='text/xml')

@app.route("/")
def home():
    return "Serveur IA Call Center opérationnel."

