import json
from pathlib import Path

import httpx
import yaml
from fastapi.testclient import TestClient

import gateway.app as gw
from actions.platform_client import (PlatformClient, district_name, format_grievance, format_jamabandi, format_lpc,
                                     format_mutation, format_parimarjan)

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def test_domain_is_consistent():
    domain = load("domain.yml")
    responses, slots = domain["responses"], domain["slots"]
    for form, spec in domain["forms"].items():
        for s in spec["required_slots"]:
            assert f"utter_ask_{s}" in responses, s
            conds = slots[s]["mappings"][0]["conditions"]
            assert {"active_loop": form, "requested_slot": s} in conds
    known = set(responses) | set(domain["actions"]) | set(domain["forms"])
    for rule in load("data/rules.yml")["rules"]:
        for step in rule["steps"]:
            if "action" in step:
                assert step["action"] in known, step["action"]
            if "intent" in step and step["intent"] != "nlu_fallback":
                assert step["intent"] in domain["intents"], step["intent"]
    nlu_intents = {i["intent"] for i in load("data/nlu.yml")["nlu"]}
    assert nlu_intents == set(domain["intents"])


def test_menu_has_six_services():
    menu = load("domain.yml")["responses"]["utter_main_menu"][0]["buttons"]
    assert sum(b["title"][0].isdigit() for b in menu) == 6


def _client(handler):
    return PlatformClient("http://platform", transport=httpx.MockTransport(handler))


def test_district_names_accept_hindi_and_case():
    assert district_name("पटना") == "Patna" and district_name("nalanda") == "Nalanda" and district_name("0") is None


def test_jamabandi_check_sends_fields_and_formats():
    def handler(req):
        body = json.loads(req.content)
        assert req.url.path.endswith("/jamabandi/check-owner") and body == {"district": "Patna", "khesra": "112", "owner": "Ram"}
        return httpx.Response(200, json={"verdict": "mismatch", "khesra": "112", "district": "Patna", "mauja": "Rampur",
                                         "khata": "31", "record_owner": "Ram Kumar Sinha", "record_owner_hi": "राम कुमार सिन्हा"})
    res = _client(handler).check_jamabandi("patna", "112", "Ram")
    assert "Ram Kumar Sinha" in format_jamabandi(res, "en") and "परिमार्जन" in format_jamabandi(res, "hi")


def test_mutation_status_found_and_missing():
    case = {"case_no": "DISP/2023/PTA/0041", "office": "DCLR Court Patna",
            "pipeline": [{"stage": "Filed", "stage_hi": "दायर", "state": "done"},
                         {"stage": "Objection Period", "stage_hi": "आपत्ति अवधि", "state": "current"}],
            "delay": {"label": "47 working days in Objection Period. High.", "label_hi": "उच्च विलंब"}}

    def handler(req):
        if req.url.path.endswith("DISP/2023/PTA/0041/status"):
            return httpx.Response(200, json=case)
        return httpx.Response(404)
    c = _client(handler)
    msg = format_mutation(c.mutation_status("disp/2023/pta/0041"), "en")
    assert "⏳ Objection Period" in msg and "High" in msg
    assert format_mutation(c.mutation_status("MUT/9"), "hi") == "यह वाद संख्या नहीं मिली।"


def test_lpc_blocked_lists_next_steps():
    c = _client(lambda req: httpx.Response(200, json={"eligible": False, "explanation": "Blocked: anomaly flag.",
                                                      "explanation_hi": "रोक", "next_steps": ["Contact the Circle Office."]}))
    msg = format_lpc(c.lpc_assess("Muzaffarpur", "502"), "en")
    assert "anomaly" in msg and "Circle Office" in msg
    assert "नहीं मिला" in format_lpc(_client(lambda r: httpx.Response(404)).lpc_assess("Gaya", "9"), "hi")


def test_grievance_skips_unknown_khesra():
    def handler(req):
        body = json.loads(req.content)
        assert body["khesra"] is None and body["district"] == "Gaya"
        return httpx.Response(200, json={"id": "GRV-2026-0004", "type": "encroachment", "priority": "P1",
                                         "assigned_title": "Anchaladhikari (CO), Bodhgaya", "acknowledgment_hi": "पावती"})
    res = _client(handler).lodge_grievance("Rekha", "gaya", "0", "My land is encroached")
    assert "Anchaladhikari" in format_grievance(res, "en") and format_grievance(res, "hi") == "पावती"


def test_parimarjan_status():
    c = _client(lambda req: httpx.Response(200, json={"status": "PRM/2025/0008 is at Field Verification", "status_hi": "क",
                                                      "next_steps": "Be available at the plot.", "next_steps_hi": "ख"}))
    assert "Field Verification" in format_parimarjan(c.parimarjan_status("prm/2025/0008"), "en")
    assert "PRM/2025/0008" in format_parimarjan(_client(lambda r: httpx.Response(404)).parimarjan_status("X"), "en")


def test_gateway_forwards_to_rasa():
    def handler(req):
        body = json.loads(req.content)
        assert body["message"] == "hi"
        return httpx.Response(200, json=[{"recipient_id": body["sender"], "text": "Namaste",
                                          "buttons": [{"title": "1. Check", "payload": "/check_jamabandi"}]}])
    gw._transport = httpx.MockTransport(handler)
    r = TestClient(gw.app).post("/api/chat", json={"message": "hi", "session_id": "s1"}).json()
    assert r["session_id"] == "s1" and r["messages"][0]["buttons"][0]["payload"] == "/check_jamabandi"
