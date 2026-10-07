# AI-Land-Governance-ChatBotAPI

Module 21 of the AI Land Governance platform: a **menu-driven Citizen ChatBot** built on Rasa,
separate from module 1 (Citizen Assistant, free-text Q&A inside the main platform).

## Menu

| # | Service | What happens |
|---|---------|--------------|
| 1 | Check Jamabandi | Asks district, khesra, name → `document-verification/jamabandi/check-owner` |
| 2 | Mutation status | Asks case number (e.g. MUT/2023/NLD/6634) → `mutation-tracker` 4-stage pipeline and delay |
| 3 | LPC eligibility | Asks district and khesra → `lpc/assess` (eligible, or the blocking reasons and next steps) |
| 4 | Lodge grievance | Asks name, district, khesra (0 if unknown), complaint → `grievance/analyze` (type, priority, routed officer, Hindi acknowledgment) |
| 5 | Parimarjan status | Explains Parimarjan, asks the application ID (e.g. PRM/2025/0008) → `parimarjan/cases/{id}/explain` |
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

## Demo values (from the platform's sample data)

- Jamabandi: Patna, khesra 112, Ram Kumar Sinha (match) or any other name (mismatch)
- Mutation: MUT/2023/NLD/6634, DISP/2023/PTA/0041 (highly delayed), MUT/2023/MUZ/7712
- LPC: Darbhanga 332 (eligible), Muzaffarpur 502 (blocked: anomaly flag)
- Parimarjan: PRM/2025/0001 to PRM/2025/0018

The bot calls the platform as role `citizen` using dev headers (platform `ALLOW_DEV_HEADERS=true`).
Set `PLATFORM_TOKEN` to a JWT from `POST /api/auth/login` to use token auth instead.

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
