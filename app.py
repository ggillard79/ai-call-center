from flask import Flask, request, Response, send_from_directory
from openai import OpenAI
import os
import tempfile
import uuid

app = Flask(__name__)

# --- CONFIGURATION OPENAI ---
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- DOSSIER AUDIO PUBLIC ---
# Render sert automatiquement le dossier /static/
AUDIO_DIR = os.path.join(os.getcwd(), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# --- UTILS TWIML ---
def twiml_play(audio_url: str, fallback_text: str = None) -> str:
    """Renvoie une réponse TwiML avec un MP3 à lire et un fallback <Say>"""
    fallback = f'<Say voice="alice" language="fr-FR">{fallback_text}</Say>' if fallback_text else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{audio_url}</Play>
  {fallback}
</Response>"""

def twiml_say(text: str) -> str:
    """Fallback Twilio TTS simple"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">{text}</Say>
</Response>"""

def generate_tts_audio(text: str) -> str:
    """Génère un MP3 via OpenAI TTS et retourne une URL publique"""
    filename = f"{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(AUDIO_DIR, filename)

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",  # alternatives : alloy, softy, spark, charlie
        input=text
    )
    response.stream_to_file(audio_path)

    # URL publique accessible par Twilio (Render expose /static/)
    base_url = request.url_root.rstrip('/')
    return f"{base_url}/static/audio/{filename}"

# --- ROUTE POUR LIRE LES AUDIO (utile si Render bloque /static/) ---
@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, mimetype="audio/mpeg")

# --- SESSION SIMPLIFIÉE ---
SESS = {}
def get_session(call_sid: str):
    if call_sid not in SESS:
        SESS[call_sid] = {"turns": 0, "context": {}}
    return SESS[call_sid]

WELCOME = (
    "Bonjour, vous êtes bien au cabinet médical du Docteur Martin. "
    "Souhaitez-vous prendre, modifier ou annuler un rendez-vous ?"
)

# --- ROUTE TWILIO ---
@app.route("/voice", methods=["POST"])
def voice():
    try:
        call_sid = request.form.get("CallSid", "")
        speech = (request.form.get("SpeechResult", "") or "").strip()
        print("CallSid:", call_sid, "| SpeechResult:", speech)

        s = get_session(call_sid)
        s["turns"] += 1

        # Si rien entendu
        if not speech:
            audio_url = generate_tts_audio(WELCOME)
            return Response(twiml_play(audio_url, fallback_text=WELCOME), mimetype="text/xml")

        low = speech.lower()

        # Intentions simples
        if any(w in low for w in ["prendre", "rendez-vous", "rdv", "nouveau"]):
            reply = "Très bien, pour quel jour souhaitez-vous votre rendez-vous ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url, fallback_text=reply), mimetype="text/xml")

        if any(w in low for w in ["annuler", "supprimer"]):
            reply = "Pouvez-vous me préciser la date du rendez-vous que vous souhaitez annuler ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url, fallback_text=reply), mimetype="text/xml")

        if any(w in low for w in ["déplacer", "changer", "modifier"]):
            reply = "D'accord, quel est le nouveau moment qui vous conviendrait mieux ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url, fallback_text=reply), mimetype="text/xml")

        # Réponse IA contextuelle
        prompt = (
            "Tu es la secrétaire d’un cabinet médical (docteur généraliste). "
            "Réponds poliment et professionnellement en français, en une à deux phrases maximum. "
            "Si possible, pose une question pour avancer dans la prise de rendez-vous "
            "(date, heure, nom du patient, médecin, ou motif). "
            f"\nPatient: {speech}\nSecrétaire:"
        )

        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = resp.choices[0].message.content.strip()
        audio_url = generate_tts_audio(reply)
        return Response(twiml_play(audio_url, fallback_text=reply), mimetype="text/xml")

    except Exception as e:
        print("🔥 ERREUR:", str(e))
        msg = "Désolé, une erreur est survenue. Veuillez rappeler plus tard."
        return Response(twiml_say(msg), mimetype="text/xml")

@app.route("/")
def home():
    return "✅ Serveur IA Call Center médical opérationnel (Twilio + OpenAI TTS v1.x)."
