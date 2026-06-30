import os
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ["GROQ_API_KEY"])

@app.post("/suggest")
def suggest():
    body = request.get_json(force=True)
    prompt = (body.get("prompt") or "").strip()
    response = (body.get("response") or "").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    system = (
        "You are an expert at identifying vague or uncertain AI responses and rewriting "
        "user questions to get more accurate, factual answers. "
        "Always return exactly a JSON array of 3 strings and nothing else."
    )
    user = (
        f'The user asked: "{prompt}"\n\n'
        f'The AI responded with signs of uncertainty:\n"{response[:800]}"\n\n'
        "Write 3 improved versions of the user's question that will produce a more "
        "accurate, confident, factual answer. Each version must use a different strategy:\n"
        "1. Ask the AI to flag anything it is uncertain about\n"
        "2. Ask for a step-by-step breakdown with sources\n"
        "3. Ask for a precise, concise, factual answer with no speculation\n\n"
        "Return only a valid JSON array of 3 strings. No explanation."
    )

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=400,
        temperature=0.4,
    )

    raw = completion.choices[0].message.content.strip()
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        return jsonify({"error": "model returned unexpected format"}), 502

    suggestions = json.loads(match.group())
    if not isinstance(suggestions, list) or len(suggestions) < 3:
        return jsonify({"error": "model returned fewer than 3 suggestions"}), 502

    return jsonify({"suggestions": suggestions[:3], "model": "llama-3.1-8b-instant"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
