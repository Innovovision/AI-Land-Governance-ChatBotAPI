"""Thin client for the AI-Land-Governance platform API. Kept free of rasa_sdk imports so it
can be unit-tested and reused by the gateway."""
import os

import httpx

PLATFORM_URL = os.getenv("PLATFORM_URL", "http://api:8000")
HEADERS = {"X-Role": "citizen", "X-User-Id": "chatbot"}


class PlatformClient:
    def __init__(self, base_url: str = PLATFORM_URL, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url, headers=HEADERS, timeout=15, transport=transport)

    def _post(self, path: str, body: dict) -> dict:
        r = self._http.post(path, json=body)
        r.raise_for_status()
        return r.json()

    def verify_jamabandi(self, mauza, khata, khesra, owner_name) -> dict:
        return self._post("/api/m/document-verification/jamabandi/verify",
                          {"mauza": mauza, "khata": khata, "khesra": khesra, "owner_name": owner_name})

    def mutation_status(self, case_no: str) -> dict | None:
        r = self._http.get(f"/api/m/mutation-tracker/cases/{case_no.strip()}/status")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def lpc_advise(self, applicant, mauza, khata, khesra) -> dict:
        return self._post("/api/m/lpc/advise",
                          {"applicant": applicant, "mauza": mauza, "khata": khata, "khesra": khesra})

    def lodge_grievance(self, citizen, mauza, text) -> dict:
        return self._post("/api/m/grievance/grievances", {"citizen": citizen, "mauza": mauza, "text": text})

    def ask(self, question: str, lang: str) -> dict:
        return self._post("/api/m/citizen-assistant/ask", {"question": question, "lang": lang})


STAGE_LABELS = {
    "applied": ("Application received", "आवेदन प्राप्त"),
    "karmachari_report": ("With Revenue Karmachari", "राजस्व कर्मचारी के पास"),
    "ci_report": ("With Circle Inspector", "अंचल निरीक्षक के पास"),
    "co_hearing": ("Hearing before Circle Officer", "अंचल अधिकारी के समक्ष सुनवाई"),
    "co_order": ("Order passed", "आदेश पारित"),
    "jamabandi_updated": ("Jamabandi updated", "जमाबंदी अद्यतन"),
}


def format_jamabandi(res: dict, lang: str) -> str:
    hi = lang == "hi"
    v = res.get("verdict")
    if v == "not_found":
        return "इस खाता/खेसरा का अभिलेख नहीं मिला।" if hi else "No record found for this khata/khesra."
    if v == "match":
        return "अभिलेख आपके नाम से मेल खाता है।" if hi else "The record matches your name."
    rec = next((c["record"] for c in res.get("checks", []) if c["field"] == "owner_name"), "")
    return (f"अभिलेख में रैयत का नाम '{rec}' है। सुधार के लिए परिमार्जन करें।" if hi
            else f"The record shows raiyat '{rec}'. If this is wrong, apply for Parimarjan.")


def format_mutation(res: dict | None, lang: str) -> str:
    hi = lang == "hi"
    if res is None:
        return "यह वाद संख्या नहीं मिली।" if hi else "Case number not found."
    label = STAGE_LABELS.get(res["stage"], (res["stage"], res["stage"]))[1 if hi else 0]
    if hi:
        msg = f"वाद {res['case_no']}: {label}। आवेदन को {res['age_days']} दिन हुए।"
        return msg + (" निर्धारित समय सीमा पार हो चुकी है।" if res["sla_breached"] and res["open"] else "")
    msg = f"Case {res['case_no']}: {label}. Filed {res['age_days']} days ago."
    return msg + (" It is past the service deadline." if res["sla_breached"] and res["open"] else "")


def format_lpc(res: dict, lang: str) -> str:
    hi = lang == "hi"
    if res.get("eligible"):
        return "आप एलपीसी के लिए पात्र प्रतीत होते हैं।" if hi else "You appear eligible for an LPC."
    head = "अभी एलपीसी नहीं बन सकता:" if hi else "An LPC can't be issued yet:"
    return head + "\n" + "\n".join(f"- {i}" for i in res.get("issues", []))


def format_grievance(res: dict, lang: str) -> str:
    if lang == "hi":
        return f"आपकी शिकायत {res['id']} दर्ज हो गई है।"
    return f"Your grievance {res['id']} has been registered."
