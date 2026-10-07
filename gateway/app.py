"""ChatBot API gateway: one stable endpoint for web, mobile and WhatsApp front-ends,
forwarding to Rasa's REST channel and normalising the reply."""
import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

RASA_URL = os.getenv("RASA_URL", "http://rasa:5005")

app = FastAPI(title="AI Land Governance ChatBot API", version="0.1.0")
_transport: httpx.BaseTransport | None = None  # tests inject a mock transport


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/chat")
def chat(body: ChatIn):
    sid = body.session_id or str(uuid.uuid4())
    try:
        with httpx.Client(base_url=RASA_URL, timeout=20, transport=_transport) as http:
            r = http.post("/webhooks/rest/webhook", json={"sender": sid, "message": body.message})
            r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Chat engine unavailable: {e.__class__.__name__}")
    messages = [{"text": m.get("text"),
                 "buttons": [{"title": b["title"], "payload": b["payload"]} for b in m.get("buttons", [])]}
                for m in r.json()]
    return {"session_id": sid, "messages": messages}
