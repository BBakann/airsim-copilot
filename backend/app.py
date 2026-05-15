from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from typing import Optional

from werkzeug.serving import WSGIRequestHandler


class _WSGIRequestHandlerQuietTelemetry(WSGIRequestHandler):
    """Mobil poll (GET /telemetry) konsolu doldurmasın diye bu satırları loglama."""

    def log_request(self, code="-", size="-"):
        if getattr(self, "path", None) == "/telemetry":
            return
        super().log_request(code, size)


app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # büyük JPEG base64 için

import os
from state import CopilotState
from copilot import Copilot

cstate = CopilotState()


def _build_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=key)
    except Exception:
        return None


copilot = Copilot(client=_build_client())

STALE_SECONDS = 8

last_telemetry = {
    "battery": 100,
    "distance": 0,
    "speed": 0,
    "altitude": 0,
    "gps": {"lat": 0, "lng": 0},
    "signalQuality": -40,
    "image": None,
    "isOnline": False,
    "last_update": 0,
}

# POST /data aralığı ve kare hızı için (monotonic)
_prev_post_mono: Optional[float] = None
_prev_image_mono: Optional[float] = None


def _field_from_client(data: dict, key: str) -> bool:
    return key in data and data[key] is not None


def _log_telemetry_post(data: dict, stored: dict) -> None:
    global _prev_post_mono, _prev_image_mono

    now_m = time.monotonic()

    raw_img = data.get("image")
    has_img = (
        isinstance(raw_img, str)
        and len(raw_img) > 100
    )

    # --- Zamanlama: her POST ve sadece görsel varken kare aralığı / FPS ---
    post_dt_s: Optional[float] = None
    if _prev_post_mono is not None:
        post_dt_s = now_m - _prev_post_mono
    _prev_post_mono = now_m

    image_dt_s: Optional[float] = None
    fps: Optional[float] = None
    if has_img:
        if _prev_image_mono is not None:
            image_dt_s = now_m - _prev_image_mono
            if image_dt_s and image_dt_s > 0:
                fps = 1.0 / image_dt_s
        _prev_image_mono = now_m

    img_chars = len(raw_img) if has_img else 0
    img_bytes_approx = int(img_chars * 0.75) if has_img else 0

    # --- Kaynak: istemci göndermediyse sunucu varsayılanı = mock ---
    bat_ok = _field_from_client(data, "battery")
    sig_ok = _field_from_client(data, "signalQuality")
    lat_ok = _field_from_client(data, "latitude")
    lng_ok = _field_from_client(data, "longitude")
    alt_ok = _field_from_client(data, "altitude")

    gps_lat = stored["gps"]["lat"]
    gps_lng = stored["gps"]["lng"]
    gps_suspicious = lat_ok and lng_ok and abs(gps_lat) < 1e-7 and abs(gps_lng) < 1e-7

    mock_bits: list[str] = []
    if not bat_ok:
        mock_bits.append("batarya→varsayılan")
    if not sig_ok:
        mock_bits.append("sinyal→varsayılan")
    if not lat_ok or not lng_ok:
        mock_bits.append("GPS→eksik/varsayılan")
    elif gps_suspicious:
        mock_bits.append("GPS→(0,0) sensör yok/hata olabilir")
    if not has_img:
        mock_bits.append("görsel→yok")

    mock_summary = (
        " | MOCK/UYARI: " + ", ".join(mock_bits)
        if mock_bits
        else " | MOCK/UYARI: yok (alanlar istemciden veya görüntü tam)"
    )

    post_interval_txt = (
        f"{post_dt_s:.2f}s önceki POST"
        if post_dt_s is not None
        else "ilk POST"
    )

    if has_img:
        kb = img_bytes_approx / 1024.0
        if image_dt_s is not None and fps is not None:
            frame_txt = f"kare aralığı {image_dt_s:.2f}s → ~{fps:.2f} FPS | ~{kb:.1f} KB (base64≈)"
        else:
            frame_txt = f"ilk kare | ~{kb:.1f} KB (base64≈)"
    else:
        frame_txt = "görsel yok"

    print(
        "\n┌── TELEMETRY POST ─────────────────────────────────────────────",
        flush=True,
    )
    print(
        f"│ Hız: {stored['speed']:.2f} m/s  |  Ön mesafe: {stored['distance']:.2f} m",
        flush=True,
    )
    print(
        f"│ Batarya: {stored['battery']:.0f}% ({'istemci' if bat_ok else 'VARSAYILAN/mock'})  |  "
        f"Sinyal: {stored['signalQuality']:.0f} dBm ({'istemci' if sig_ok else 'VARSAYILAN/mock'})",
        flush=True,
    )
    gps_src = "istemci" if (lat_ok and lng_ok) else "eksik/mock"
    alt_src = "istemci" if alt_ok else "varsayılan/mock"
    print(
        f"│ Konum: lat={gps_lat:.6f}, lng={gps_lng:.6f} ({gps_src})  |  "
        f"Yükseklik: {stored['altitude']:.1f} m ({alt_src})",
        flush=True,
    )
    print(f"│ Görsel: {frame_txt}", flush=True)
    print(f"│ POST sıklığı: {post_interval_txt}", flush=True)
    print(f"│{mock_summary}", flush=True)
    print(
        "└──────────────────────────────────────────────────────────────\n",
        flush=True,
    )


@app.route("/data", methods=["POST"])
def receive_data():
    global last_telemetry
    data = request.get_json()

    if not data:
        return jsonify({"error": "no json"}), 400

    lat = data.get("latitude")
    lng = data.get("longitude")
    gps = dict(last_telemetry["gps"])
    if lat is not None and lng is not None:
        try:
            gps = {"lat": float(lat), "lng": float(lng)}
        except (TypeError, ValueError):
            pass

    last_telemetry = {
        "battery": float(data.get("battery", 100)),
        "distance": float(data.get("distance", 0)),
        "speed": float(data.get("speed", 0)),
        "altitude": float(data.get("altitude", 0)),
        "gps": gps,
        "signalQuality": float(data.get("signalQuality", -40)),
        "image": data.get("image"),
        "isOnline": True,
        "last_update": int(time.time()),
    }

    _log_telemetry_post(data, last_telemetry)
    return jsonify({"status": "ok"}), 200


@app.route("/telemetry", methods=["GET"])
def get_telemetry():
    if last_telemetry["last_update"] and (
        time.time() - last_telemetry["last_update"] > STALE_SECONDS
    ):
        last_telemetry["isOnline"] = False
    return jsonify(last_telemetry), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"}), 200


@app.route("/command", methods=["POST"])
def post_command():
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if not text or not isinstance(text, str):
        return jsonify({"error": "text gerekli"}), 400
    d = copilot.parse_command(text)
    cstate.set_directive(
        mode=d["mode"], bias=d["bias"], speed_cap=d["speed_cap"],
        target=d["target"], stop_on=d["stop_on"], ttl=d["ttl"],
    )
    return jsonify({"status": "ok", "directive": cstate.get_directive()}), 200


@app.route("/directive", methods=["GET"])
def get_directive():
    return jsonify(cstate.get_directive()), 200


@app.route("/estop", methods=["GET", "POST"])
def estop():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        cstate.set_estop(not bool(data.get("clear", False)))
        return jsonify({"status": "ok", "estop": cstate.is_estop()}), 200
    return jsonify({"estop": cstate.is_estop()}), 200


@app.route("/copilot/event", methods=["POST"])
def copilot_event():
    data = request.get_json(silent=True) or {}
    image = data.get("image")
    if not image:
        return jsonify({"error": "image gerekli"}), 400
    out = copilot.analyze_event(
        image_b64=image,
        telemetry=data.get("telemetry", {}),
        state=data.get("state", "?"),
        prev_state=data.get("prev_state", "?"),
    )
    cstate.append_log(out)
    if out.get("directive"):
        d = out["directive"]
        cstate.set_directive(
            mode=d["mode"], bias=d["bias"], speed_cap=d["speed_cap"],
            target=d["target"], stop_on=d["stop_on"], ttl=d["ttl"],
        )
    return jsonify(out), 200


@app.route("/copilot/stream", methods=["GET"])
def copilot_stream():
    try:
        since = float(request.args.get("since", 0))
    except (TypeError, ValueError):
        since = 0.0
    return jsonify({"events": cstate.log_since(since)}), 200


@app.route("/copilot/ask", methods=["POST"])
def copilot_ask():
    data = request.get_json(silent=True) or {}
    image = data.get("image") or (last_telemetry.get("image") or "")
    if not image:
        return jsonify({"error": "kare yok"}), 400
    out = copilot.analyze_event(
        image_b64=image,
        telemetry=last_telemetry,
        state=data.get("question", "kullanıcı sorusu"),
        prev_state="ASK",
    )
    cstate.append_log(out)
    return jsonify(out), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        threaded=True,
        request_handler=_WSGIRequestHandlerQuietTelemetry,
    )
