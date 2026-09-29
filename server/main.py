import base64
import io
import threading
from contextlib import asynccontextmanager

import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from matcha.cli import (
    MATCHA_URLS,
    SINGLESPEAKER_MODEL,
    VOCODER_URLS,
    load_matcha,
    load_vocoder,
    process_text,
    to_waveform,
)
from matcha.utils.utils import assert_model_downloaded, get_user_data_dir

MODEL_NAME = "akyl_ai"
SAMPLE_RATE = 22050

state = {}
# The model is not safe to run concurrently; serialise synthesis requests.
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vocoder_name = SINGLESPEAKER_MODEL[MODEL_NAME]["vocoder"]
    save_dir = get_user_data_dir()
    model_path = save_dir / f"{MODEL_NAME}.ckpt"
    vocoder_path = save_dir / vocoder_name
    assert_model_downloaded(model_path, MATCHA_URLS[MODEL_NAME])
    assert_model_downloaded(vocoder_path, VOCODER_URLS[vocoder_name])

    state["device"] = device
    state["model"] = load_matcha(MODEL_NAME, model_path, device)
    state["vocoder"], state["denoiser"] = load_vocoder(vocoder_name, vocoder_path, device)
    yield
    state.clear()


app = FastAPI(title="AkylAI TTS", lifespan=lifespan)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    speaking_rate: float = Field(default=SINGLESPEAKER_MODEL[MODEL_NAME]["speaking_rate"], gt=0, le=3)
    temperature: float = Field(default=0.667, ge=0, le=2)
    steps: int = Field(default=10, ge=1, le=100)


class TTSResponse(BaseModel):
    audio: str  # base64-encoded WAV
    mime_type: str = "audio/wav"
    sample_rate: int = SAMPLE_RATE
    duration: float


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/api/tts", response_model=TTSResponse)
@torch.inference_mode()
def tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")

    with lock:
        processed = process_text(0, text, state["device"])
        output = state["model"].synthesise(
            processed["x"],
            processed["x_lengths"],
            n_timesteps=req.steps,
            temperature=req.temperature,
            spks=None,
            length_scale=req.speaking_rate,
        )
        waveform = to_waveform(output["mel"], state["vocoder"], state["denoiser"]).numpy()

    buf = io.BytesIO()
    sf.write(buf, waveform, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return TTSResponse(
        audio=base64.b64encode(buf.getvalue()).decode("ascii"),
        duration=round(len(waveform) / SAMPLE_RATE, 2),
    )
