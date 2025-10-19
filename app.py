from flask import Flask, request, Response
import openai
import os

app = Flask(__name__)
# --- UTILS TWIML (à coller juste après app = Flask(__name__)) ---
def twiml_say(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">{text}</Say>
</Response>"""

def twiml_gather(prompt_text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" language="fr-FR" speechTimeout="auto" timeout="7"
          action="/voice" method="POST"
          hints="prendre rendez-vous, annuler, demain, aujourd'hui, matin, après-midi, 10h, 15h, coupe, couleur, brushing">
    <Say voice="alice" language="fr-FR">{prompt_text}</Say>
    <Pause length="1"/>
  </Gather>
  <Say voice="alice" language="fr-FR">Je n'ai pas entendu. Pourriez-vous répéter ?</Say>
</Response>"""
# --- SESSION SIMPLE EN MÉMOIRE (remplaçable par Redis plus tard) ---
SESS = {}
def get_session(call_sid: str):
    if call_sid not in SESS:
        SESS[call_sid] = {"turns": 0, "context": {}}
    return SESS[call_sid]

WELCOME = "Bonjour, vous êtes bien chez Harmonie. Dites votre demande, par exemple : prendre rendez-vous demain après-midi."

openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/voice", methods=["POST"])
def voice():
    try:
        call_sid = request.form.get("CallSid", "")
        speech = (request.form.get("SpeechResult", "") or "").strip()
        digits = request.form.get("Digits")  # utile si Twilio Trial demande d'appuyer

        # Debug minimal dans les logs Render
        print("CallSid:", call_sid, "| Digits:", digits, "| SpeechResult:", speech)

        s = get_session(call_sid)
        s["turns"] += 1

        # Si on n'a rien entendu, (re)poser l’invite
        if not speech:
            return Response(twiml_gather(WELCOME), mimetype='text/xml')

        # 🔎 Règle simple de compréhension "date/heure" (avant IA)
        low = speech.lower()
        if any(w in low for w in ["demain", "aujourd", "matin", "après-midi", "apres-midi", "h "]):
            # Ici on ne fait pas encore la réservation, on confirme juste l'intention.
            reply = f"Très bien, j'ai noté votre préférence : « {speech} ». Souhaitez-vous que je confirme ce rendez-vous ?"
            return Response(twiml_gather(reply), mimetype='text/xml')

        # 🤖 Appel IA (réponse courte + question)
        prompt = (
            "Tu es la réceptionniste du salon Harmonie. "
            "Réponds en français, de manière très concise (1-2 phrases), "
            "et termine toujours par une question claire pour avancer."
            f"\nClient: {speech}\nRéceptionniste:"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = resp["choices"][0]["message"]["content"].strip()

        return Response(twiml_gather(reply), mimetype='text/xml')

    except Exception as e:
        print("🔥 ERREUR:", str(e))
        return Response(twiml_say("Désolé, une erreur est survenue avec l'intelligence artificielle."), mimetype='text/xml')


@app.route("/")
def home():
    return "Serveur IA Call Center opérationnel."
