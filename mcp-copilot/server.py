from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

import client

BASE = os.environ.get("MCP_BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")

mcp = FastMCP("copilot")


@mcp.tool()
def get_telemetry() -> dict:
    """Aracın son telemetrisi (hız, mesafe, batarya, GPS, online)."""
    return client.get_telemetry(BASE)


@mcp.tool()
def get_directive() -> dict:
    """Aracın o anki üst-seviye hedefi (mode/bias/speed_cap)."""
    return client.get_directive(BASE)


@mcp.tool()
def send_command(text: str) -> dict:
    """Doğal dil komutu gönder (ör. 'sola git', 'yavaşla', 'dur')."""
    return client.send_command(BASE, text)


@mcp.tool()
def set_estop(on: bool) -> dict:
    """Acil dur: on=True durdurur, on=False devam ettirir."""
    return client.set_estop(BASE, on)


@mcp.tool()
def ask_copilot(question: str) -> dict:
    """Son kareye bakarak kopilota soru sor (anlatım/risk döner)."""
    return client.ask_copilot(BASE, question)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
