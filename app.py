from flask import Flask, request, Response, send_file
import openai
import os
import tempfile

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- UTILS TWIML ---
def twiml_play(audio_url: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{audio_url}</Play>
</Response>"""

def generate_tts_audio(text: str) -> str:
    """Génère un MP3 avec la voix naturelle OpenAI"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        audio_path = tmp.name
    with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=text
    ) as response:
        response.stream_to_file(audio_path)
    filename = os.path.basename(audio_path)
    return f"/audio/{filename}"

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_file(os.path.join(tempfile.gettempdir(), filename), mimetype="audio/mpeg")

# --- SESSIONS ---
SESS = {}
def get_session(call_sid: str):
    if call_sid not in SESS:
        SESS[call_sid] = {"turns": 0, "context": {}}
    return SESS[call_sid]

WELCOME = (
    "Bonjour, vous êtes bien au cabinet médical du Docteur Martin. "
    "Souhaitez-vous prendre, modifier ou annuler un rendez-vous ?"
)

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
            return Response(twiml_play(audio_url), mimetype='text/xml')

        low = speech.lower()

        # --- Reconnaissance d'intentions simples ---
        if any(w in low for w in ["prendre", "rendez-vous", "rdv", "nouveau"]):
            reply = "Très bien, pour quel jour souhaitez-vous votre rendez-vous ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url), mimetype='text/xml')

        if any(w in low for w in ["annuler", "supprimer"]):
            reply = "Pouvez-vous me préciser la date du rendez-vous que vous souhaitez annuler ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url), mimetype='text/xml')

        if any(w in low for w in ["déplacer", "changer", "modifier"]):
            reply = "D'accord, quel est le nouveau moment qui vous conviendrait mieux ?"
            audio_url = generate_tts_audio(reply)
            return Response(twiml_play(audio_url), mimetype='text/xml')

        # --- Réponse IA contextuelle ---
        prompt = (
            "Tu es la secrétaire d’un cabinet médical (docteur généraliste). "
            "Réponds poliment et professionnellement en français, en une à deux phrases maximum. "
            "Si possible, pose une question pour avancer dans la prise de rendez-vous "
            "(date, heure, nom du patient, médecin, ou motif). "
            f"\nPatient: {speech}\nSecrétaire:"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = resp["choices"][0]["message"]["content"].strip()

        audio_url = generate_tts_audio(reply)
        return Response(twiml_play(audio_url), mimetype='text/xml')

    except Exception as e:
        print("🔥 ERREUR:", str(e))
        err_audio = generate_tts_audio("Désolé, une erreur est survenue. Veuillez rappeler plus tard.")
        return Response(twiml_play(err_audio), mimetype='text/xml')


@app.route("/")
def home():
    return "Serveur IA Call Center médical opérationnel (voix naturelle)."
