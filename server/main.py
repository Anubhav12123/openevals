from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI(title="OpenEvals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

client = Groq(api_key=os.environ["GROQ_API_KEY"])

class SuggestRequest(BaseModel):
    prompt: str
    response: str

class SuggestResponse(BaseModel):
    suggestions: list[str]
    model: str = "llama-3.1-8b-instant"

@app.post("/suggest", response_model=SuggestResponse)
async def suggest(body: SuggestRequest):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")

    system = (
        "You are an expert at identifying vague or uncertain AI responses and rewriting "
        "user questions to get more accurate, factual answers. "
        "Always return exactly a JSON array of 3 strings and nothing else."
    )

    user = (
        f'The user asked: "{body.prompt}"\n\n'
        f'The AI responded with signs of uncertainty:\n"{body.response[:800]}"\n\n'
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
            {"role": "user",   "content": user},
        ],
        max_tokens=400,
        temperature=0.4,
    )

    raw = completion.choices[0].message.content.strip()

    import json, re
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        raise HTTPException(status_code=502, detail="Model returned unexpected format")

    suggestions = json.loads(match.group())
    if not isinstance(suggestions, list) or len(suggestions) < 3:
        raise HTTPException(status_code=502, detail="Model returned fewer than 3 suggestions")

    return SuggestResponse(suggestions=suggestions[:3])


@app.get("/health")
async def health():
    return {"status": "ok"}
