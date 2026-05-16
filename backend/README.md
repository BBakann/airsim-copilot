# backend — Flask Kopilot Hub

Tek sunucu (:5000). Sim yazar, mobil + MCP okur. Otonomi burada YOK.

## Dosyalar
- `app.py` — HTTP yüzey (tüm route'lar), modül durum nesneleri
- `state.py` — CopilotState: TTL directive + estop + log (thread-safe)
- `video_state.py` — VideoState: view->jpeg kare (thread-safe)
- `copilot.py` — tek Anthropic noktası (parse_command / analyze_event)
- `conftest.py` — pytest import path
- `tests/` — 31 test, Anthropic mock ($0)
- `COPILOT_DEV.md` — manuel e2e

## Çalıştır
```
set PYTHONIOENCODING=utf-8
set ANTHROPIC_API_KEY=...   # opsiyonel; yoksa kopilot 'çevrimdışı' degrade
..\.venv\Scripts\python.exe app.py
```

## Test
```
..\.venv\Scripts\python.exe -m pytest -q
```
