"""Custom actions: submit each form to the platform API and reset the form's slots."""
from typing import Any

import httpx
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.platform_client import (PlatformClient, format_grievance, format_jamabandi, format_lpc,
                                     format_mutation, format_parimarjan)

client = PlatformClient()


class _Submit(Action):
    slots: list[str] = []

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]):
        lang = tracker.get_slot("language") or "en"
        values = {s: (tracker.get_slot(s) or "").strip() for s in self.slots}
        try:
            dispatcher.utter_message(text=self.call(values, lang))
        except httpx.HTTPError:
            dispatcher.utter_message(response="utter_service_down")
        return [SlotSet(s, None) for s in self.slots]

    def call(self, v: dict, lang: str) -> str:
        raise NotImplementedError


class ActionSubmitJamabandi(_Submit):
    slots = ["district", "khesra", "owner_name"]

    def name(self):
        return "action_submit_jamabandi"

    def call(self, v, lang):
        return format_jamabandi(client.check_jamabandi(v["district"], v["khesra"], v["owner_name"]), lang)


class ActionSubmitMutation(_Submit):
    slots = ["case_no"]

    def name(self):
        return "action_submit_mutation"

    def call(self, v, lang):
        return format_mutation(client.mutation_status(v["case_no"]), lang)


class ActionSubmitLpc(_Submit):
    slots = ["district", "khesra"]

    def name(self):
        return "action_submit_lpc"

    def call(self, v, lang):
        return format_lpc(client.lpc_assess(v["district"], v["khesra"]), lang)


class ActionSubmitGrievance(_Submit):
    slots = ["owner_name", "district", "plot_no", "grievance_text"]

    def name(self):
        return "action_submit_grievance"

    def call(self, v, lang):
        return format_grievance(client.lodge_grievance(v["owner_name"], v["district"], v["plot_no"],
                                                       v["grievance_text"]), lang)


class ActionSubmitParimarjan(_Submit):
    slots = ["prm_case_id"]

    def name(self):
        return "action_submit_parimarjan"

    def call(self, v, lang):
        return format_parimarjan(client.parimarjan_status(v["prm_case_id"]), lang)


class ActionSubmitAssistant(_Submit):
    slots = ["question"]

    def name(self):
        return "action_submit_assistant"

    def call(self, v, lang):
        return client.ask(v["question"], lang)["answer"]
