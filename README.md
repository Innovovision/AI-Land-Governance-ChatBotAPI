# AI-Land-Governance-ChatBotAPI

Module 21 of the AI Land Governance platform: a **menu-driven Citizen ChatBot** built on Rasa,
separate from module 1 (Citizen Assistant, free-text Q&A inside the main platform).

## Menu

| # | Service | What happens |
|---|---------|--------------|
| 1 | Check Jamabandi | Asks mauza, khata, khesra, name → platform `document-verification` |
| 2 | Mutation status | Asks case number → platform `mutation-tracker` |
| 3 | LPC eligibility | Asks name and plot → platform `lpc/advise` |
| 4 | Lodge grievance | Asks name, mauza, complaint → platform `grievance` |
| 5 | Parimarjan help | Static guidance |
| 6 | Ask a question | Hands free text to platform module 1 (Citizen Assistant) |

Hindi and English are supported (menu buttons switch the `language` slot). Typing the option
number or `menu` / `0` works on SMS-style channels.

## Layout

```
config.yml, domain.yml, data/          Rasa 3.6 project (NLU, rules, forms)
actions/actions.py                     custom actions (rasa_sdk)
actions/platform_client.py             HTTP client + message formatting for the platform API
gateway/app.py                         FastAPI "ChatBot API": POST /api/chat → Rasa REST channel
tests/                                 domain consistency, client and gateway tests (no Rasa needed)
```

## Run

```bash
# 1. Start the platform API (other repo) on :8000
# 2. Train and start the bot
docker compose run --rm rasa train
docker compose up
# 3. Talk to it
curl -s localhost:8080/api/chat -H 'content-type: application/json' -d '{"message":"hi"}'
```

Rasa 3.6 needs Python 3.8–3.10 if you run it outside Docker.

## Test

```bash
pip install -r requirements-dev.txt
pytest
```
