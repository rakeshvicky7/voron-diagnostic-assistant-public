"""Optional voice for the assistant. Both parts run fully offline on the processor (the GPU stays free for the model).

 Speech -> text : faster-whisper   https://github.com/SYSTRAN/faster-whisper   (pip install faster-whisper)
 Text -> speech : Piper            https://github.com/OHF-Voice/piper1-gpl     (pip install piper-tts + one voice file
                                   in data/voices, e.g. en_US-lessac-medium.onnx)
If a package is missing, the assistant falls back to the browser's own speech functions, so it always works.
"""
import io, os, wave, tempfile, pathlib, threading
A = pathlib.Path(__file__).resolve().parents[1]
VOICES = A / "data" / "voices"
WHISPER_SIZE = os.environ.get("WHISPER_MODEL", "small.en")   # tiny.en / base.en are faster, small.en is more accurate
_stt = _tts = None; _lock = threading.Lock()

def status():
    s = {"stt": False, "tts": False, "stt_note": "", "tts_note": ""}
    try: import faster_whisper; s["stt"] = True   # noqa
    except Exception: s["stt_note"] = "faster-whisper not installed: the browser's speech recognition is used instead"
    try:
        import piper  # noqa
        s["tts"] = bool(list(VOICES.glob("*.onnx")))
        if not s["tts"]: s["tts_note"] = "Piper installed but no voice file in data/voices"
    except Exception: s["tts_note"] = "piper-tts not installed: the browser's own voice is used instead"
    return s

def transcribe(audio: bytes, suffix=".webm") -> str:
    global _stt
    from faster_whisper import WhisperModel
    with _lock:
        if _stt is None: _stt = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")   # downloads once (~500 MB for small.en)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f: f.write(audio); p = f.name
        try:
            segs, _ = _stt.transcribe(p, beam_size=5, vad_filter=True,
                                      initial_prompt="Voron 3D printer, hotend, thermistor, extruder, nozzle, Klipper, umbilical, gantry, belt.")
            return " ".join(s.text.strip() for s in segs).strip()
        finally:
            try: os.remove(p)
            except OSError: pass

def speak(text: str) -> bytes:
    global _tts
    from piper import PiperVoice
    with _lock:
        if _tts is None: _tts = PiperVoice.load(str(sorted(VOICES.glob("*.onnx"))[0]))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w: _tts.synthesize_wav(text, w)
        return buf.getvalue()
