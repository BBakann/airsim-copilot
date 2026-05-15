# Copilot backend — manuel e2e

## Gereksinim
- Anthropic Console: ödeme + **spend limit (ör. $5)** ayarlı
- `set ANTHROPIC_API_KEY=...` (yoksa kopilot "çevrimdışı" döner, sürüş etkilenmez)

## Çalıştırma
```
set PYTHONIOENCODING=utf-8
set ANTHROPIC_API_KEY=sk-ant-...
"...\.venv\Scripts\python.exe" backend\app.py
```

## Smoke (key olmadan, $0)
- `GET /directive` -> explore default
- `POST /estop {}` -> estop true; `POST /estop {"clear":true}` -> false
- `POST /command {"text":"sola git"}` -> 200 (key yoksa explore default döner)
- `POST /copilot/event {"image":"<b64>","state":"BRAKING","prev_state":"DRIVING"}`
  -> key yoksa risk "unknown", sürüş etkilenmez

## Smoke (key ile)
- `POST /command {"text":"on metre ileri yavaş git"}` -> directive goto/speed_cap düşük
- `/copilot/stream?since=0` -> anlatım kayıtları
