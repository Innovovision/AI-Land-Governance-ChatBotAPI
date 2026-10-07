import json
from pathlib import Path

import httpx
import yaml
from fastapi.testclient import TestClient

import gateway.app as gw
from actions.platform_client import PlatformClient, format_lpc, format_mutation

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


def test_mutation_status_found_and_missing():
    def handler(req):
        if req.url.path.endswith("MUT/1/status"):
            return httpx.Response(200, json={"case_no": "MUT/1", "stage": "ci_report", "age_days": 50,
                                             "sla_breached": True, "open": True})
        return httpx.Response(404)
    c = _client(handler)
    assert "past the service deadline" in format_mutation(c.mutation_status("MUT/1"), "en")
    assert format_mutation(c.mutation_status("MUT/9"), "hi") == "यह वाद संख्या नहीं मिली।"


def test_lpc_message_lists_issues():
    c = _client(lambda req: httpx.Response(200, json={"eligible": False, "issues": ["Rent pending"]}))
    msg = format_lpc(c.lpc_advise("A", "Rampur", "12", "346"), "en")
    assert "Rent pending" in msg


def test_gateway_forwards_to_rasa():
    def handler(req):
        body = json.loads(req.content)
        assert body["message"] == "hi"
        return httpx.Response(200, json=[{"recipient_id": body["sender"], "text": "Namaste",
                                          "buttons": [{"title": "1. Check", "payload": "/check_jamabandi"}]}])
    gw._transport = httpx.MockTransport(handler)
    r = TestClient(gw.app).post("/api/chat", json={"message": "hi", "session_id": "s1"}).json()
    assert r["session_id"] == "s1" and r["messages"][0]["buttons"][0]["payload"] == "/check_jamabandi"
