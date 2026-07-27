"""
TTS provider layer — v2 + v3 compatible.

Contract unchanged: (text, lang, voice_config) ->
    {"audio_path", "duration_sec", "words":[{"text","start","end"}]}

v3 notes:
  - stability accepts only 0.0 / 0.5 / 1.0 (Creative / Natural / Robust)
  - no `speed` setting; pacing is directed via audio tags in the text
  - audio tags like [somber] [pause] [sighs] control delivery and are
    stripped from the word timeline automatically
  - timestamps: tries /with-timestamps first; if unavailable for v3,
    falls back to plain TTS + Scribe STT forced alignment
"""

import base64
import io
import json
import os
import re
from pathlib import Path

import requests

ELEVEN_BASE = "https://api.elevenlabs.io/v1"

_CJK = re.compile(r"[\u3000-\u9fff\uf900-\ufaff]")
_TAG = re.compile(r"\[[a-zA-Z ]+\]\s*")


def _chars_to_words(chars, starts, ends, lang):
    """v3 的 [somber] [pause] 等標籤會出現在 alignment 裡,
    用狀態機在拼字階段就跳過方括號內所有字元。"""
    words = []
    in_tag = False
    cur = None
    for ch, s, e in zip(chars, starts, ends):
        if ch == "[":
            in_tag = True
            continue
        if in_tag:
            if ch == "]":
                in_tag = False
            continue
        if ch.strip() == "":
            cur = None
            continue
        if lang in ("zh", "ja"):
            if _CJK.match(ch) or not words:
                words.append({"text": ch, "start": round(s, 3), "end": round(e, 3)})
            else:
                words[-1]["text"] += ch
                words[-1]["end"] = round(e, 3)
        else:
            if cur is None:
                cur = {"text": ch, "start": round(s, 3), "end": round(e, 3)}
                words.append(cur)
            else:
                cur["text"] += ch
                cur["end"] = round(e, 3)
    return words


def _voice_settings(voice_config: dict, is_v3: bool) -> dict:
    if is_v3:
        # v3: stability must be exactly 0.0, 0.5 or 1.0
        raw = float(voice_config.get("stability", 0.0))
        snapped = min([0.0, 0.5, 1.0], key=lambda v: abs(v - raw))
        return {"stability": snapped}
    return {
        "stability": voice_config.get("stability", 0.55),
        "similarity_boost": voice_config.get("similarity_boost", 0.8),
        "speed": voice_config.get("speed", 0.9),
    }


def _scribe_align(audio_bytes: bytes, api_key: str, lang: str):
    """Fallback alignment: transcribe the generated audio with Scribe to
    recover word-level timestamps when the TTS endpoint can't return them."""
    r = requests.post(
        f"{ELEVEN_BASE}/speech-to-text",
        headers={"xi-api-key": api_key},
        data={"model_id": "scribe_v1", "language_code": lang},
        files={"file": ("vo.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    words = []
    for w in data.get("words", []):
        if w.get("type") == "spacing":
            continue
        txt = w["text"].strip()
        if not txt:
            continue
        if lang in ("zh", "ja"):
            # split multi-char tokens evenly so per-character reveal still works
            n = len(txt)
            span = (w["end"] - w["start"]) / max(n, 1)
            for i, ch in enumerate(txt):
                words.append({
                    "text": ch,
                    "start": round(w["start"] + i * span, 3),
                    "end": round(w["start"] + (i + 1) * span, 3),
                })
        else:
            words.append({"text": txt, "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return words


def tts_elevenlabs(text: str, lang: str, voice_config: dict, out_path: Path) -> dict:
    api_key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = voice_config["voice_id"]
    model_id = voice_config.get("model_id", "eleven_multilingual_v2")
    is_v3 = model_id.startswith("eleven_v3")

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": _voice_settings(voice_config, is_v3),
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    # attempt 1: timestamps endpoint
    r = requests.post(
        f"{ELEVEN_BASE}/text-to-speech/{voice_id}/with-timestamps",
        headers=headers, json=payload, timeout=180,
    )
    if r.ok:
        data = r.json()
        audio = base64.b64decode(data["audio_base64"])
        out_path.write_bytes(audio)
        align = data["alignment"]
        words = _chars_to_words(
            align["characters"],
            align["character_start_times_seconds"],
            align["character_end_times_seconds"],
            lang,
        )
    else:
        print(f"with-timestamps unavailable for {model_id} "
              f"({r.status_code}), falling back to plain TTS + Scribe alignment")
        r2 = requests.post(
            f"{ELEVEN_BASE}/text-to-speech/{voice_id}",
            headers=headers, json=payload, timeout=180,
        )
        r2.raise_for_status()
        audio = r2.content
        out_path.write_bytes(audio)
        words = _scribe_align(audio, api_key, lang)

    # 兜底清洗: Scribe 路線若把標籤轉寫出來也一併洗掉
    for w in words:
        w["text"] = _TAG.sub("", w["text"]).replace("[", "").replace("]", "")
    words = [w for w in words if w["text"]]

    duration = words[-1]["end"] if words else 0.0
    return {"audio_path": str(out_path), "duration_sec": duration, "words": words}


def tts_minimax(text, lang, voice_config, out_path):
    raise NotImplementedError("Implement MiniMax T2A here if switching providers.")


PROVIDERS = {"elevenlabs": tts_elevenlabs, "minimax": tts_minimax}
