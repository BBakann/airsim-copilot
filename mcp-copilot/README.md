# Copilot MCP Server

Backend'i (Faz 1, :5000) Claude Code'a tool olarak açar.

## Önkoşul
Backend çalışıyor olmalı (`backend/app.py`). Sim/mobil şart değil.

## Çalıştırma (elle test)
```
set PYTHONIOENCODING=utf-8
set MCP_BACKEND_URL=http://127.0.0.1:5000
"...\.venv\Scripts\python.exe" mcp-copilot\server.py
```
(stdio bekler; Claude Code başlatır, normalde elle çalıştırılmaz.)

## Claude Code'a kayıt
Proje kökünde `.mcp.json` (veya `claude mcp add`):

```json
{
  "mcpServers": {
    "copilot": {
      "command": "c:\\Users\\Berdan\\OneDrive\\Masaüstü\\robot-project\\.venv\\Scripts\\python.exe",
      "args": ["c:\\Users\\Berdan\\OneDrive\\Masaüstü\\robot-project\\mcp-copilot\\server.py"],
      "env": { "MCP_BACKEND_URL": "http://127.0.0.1:5000", "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Claude Code yeniden başlat → araçlar görünür:
`get_telemetry, get_directive, send_command, set_estop, ask_copilot`.

## Araçlar
- get_telemetry() — son telemetri
- get_directive() — aktif directive
- send_command(text) — NL komut (ANTHROPIC_API_KEY yoksa explore default)
- set_estop(on) — True dur / False devam
- ask_copilot(question) — son kareye bakıp anlat
