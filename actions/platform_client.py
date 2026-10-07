"""Thin client for the AI-Land-Governance platform API. Kept free of rasa_sdk imports so it
can be unit-tested and reused by the gateway."""
import os

import httpx

PLATFORM_URL = os.getenv("PLATFORM_URL", "http://api:8000")
# The platform accepts these dev headers while ALLOW_DEV_HEADERS=true; set PLATFORM_TOKEN to use a JWT instead.
HEADERS = ({"Authorization": "Bearer " + os.environ["PLATFORM_TOKEN"]} if os.getenv("PLATFORM_TOKEN")
           else {"X-Role": "citizen", "X-User-Id": "chatbot"})
SKIP = {"", "0", "skip", "no", "none", "nahi", "नहीं", "पता नहीं"}


def optional(v: str | None) -> str | None:
    return None if (v or "").strip().lower() in SKIP else v.strip()


def district_name(v: str | None) -> str | None:
    """Accept Hindi or any-case English district names."""
    v = optional(v)
    if not v:
        return None
    hi = {"पटना": "Patna", "नालंदा": "Nalanda", "गया": "Gaya", "मुजफ्फरपुर": "Muzaffarpur",
          "दरभंगा": "Darbhanga", "नवादा": "Nawada"}
    return hi.get(v, v.title())


class PlatformClient:
    def __init__(self, base_url: str = PLATFORM_URL, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url, headers=HEADERS, timeout=20, transport=transport)

    def _post(self, path: str, body: dict) -> dict | None:
        r = self._http.post(path, json=body)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def check_jamabandi(self, district, khesra, owner) -> dict:
        return self._post("/api/m/document-verification/jamabandi/check-owner",
                          {"district": district_name(district), "khesra": khesra, "owner": owner})

    def mutation_status(self, case_no: str) -> dict | None:
        r = self._http.get(f"/api/m/mutation-tracker/cases/{case_no.strip().upper()}/status")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def lpc_assess(self, district, khesra) -> dict | None:
        return self._post("/api/m/lpc/assess", {"district": district_name(district), "khesra": khesra})

    def lodge_grievance(self, citizen, district, khesra, text) -> dict:
        return self._post("/api/m/grievance/analyze", {"citizen": citizen, "district": district_name(district),
                                                       "khesra": optional(khesra), "text": text})

    def parimarjan_status(self, case_id: str) -> dict | None:
        return self._post(f"/api/m/parimarjan/cases/{case_id.strip().upper()}/explain", {})

    def ask(self, question: str, lang: str) -> dict:
        return self._post("/api/m/citizen-assistant/ask", {"question": question, "lang": lang})


def format_jamabandi(res: dict, lang: str) -> str:
    hi = lang == "hi"
    if res["verdict"] == "not_found":
        return "इस जिले में यह खेसरा नहीं मिला।" if hi else "No record found for this khesra in that district."
    place = f"{res['mauja']}, {res['district']}"
    if res["verdict"] == "match":
        return (f"खेसरा {res['khesra']} ({place}, खाता {res['khata']}) आपके नाम पर दर्ज है। रकबा {res['area_acre']} एकड़, "
                f"स्थिति: {res['status_hi']}।" if hi else
                f"Khesra {res['khesra']} ({place}, khata {res['khata']}) is recorded in your name. "
                f"Area {res['area_acre']} acre, status: {res['status']}.")
    return (f"अभिलेख में खेसरा {res['khesra']} ({place}) का रैयत '{res['record_owner_hi']}' है। "
            "यदि यह गलत है तो परिमार्जन के लिए आवेदन करें।" if hi else
            f"The record shows khesra {res['khesra']} ({place}) in the name of '{res['record_owner']}'. "
            "If this is wrong, apply for Parimarjan.")


def format_mutation(res: dict | None, lang: str) -> str:
    hi = lang == "hi"
    if res is None:
        return "यह वाद संख्या नहीं मिली।" if hi else "Case number not found."
    steps = " → ".join(("✅ " if s["state"] == "done" else "⏳ " if s["state"] == "current" else "⬜ ")
                       + (s["stage_hi"] if hi else s["stage"]) for s in res["pipeline"])
    d = res["delay"]
    return f"{res['case_no']} ({res['office']})\n{steps}\n{d['label_hi'] if hi else d['label']}"


def format_lpc(res: dict | None, lang: str) -> str:
    hi = lang == "hi"
    if res is None:
        return "इस जिले में यह खेसरा नहीं मिला।" if hi else "No record found for this khesra in that district."
    text = res["explanation_hi"] if hi else res["explanation"]
    if not res["eligible"] and res.get("next_steps"):
        text += "\n" + ("आगे क्या करें: " if hi else "Next steps: ") + " ".join(res["next_steps"])
    return text


def format_grievance(res: dict, lang: str) -> str:
    if lang == "hi":
        return res["acknowledgment_hi"]
    return (f"Your grievance {res['id']} is registered as {res['type'].replace('_', ' ')} (priority {res['priority']}) "
            f"and assigned to {res['assigned_title']}. You will get an update within 7 working days.")


def format_parimarjan(res: dict | None, lang: str) -> str:
    hi = lang == "hi"
    if res is None:
        return ("यह परिमार्जन आवेदन संख्या नहीं मिली (जैसे PRM/2025/0008)।" if hi
                else "Parimarjan case not found. Case IDs look like PRM/2025/0008.")
    return "\n".join([res["status_hi"], res["next_steps_hi"]] if hi else [res["status"], res["next_steps"]])


