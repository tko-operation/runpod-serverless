import base64
import os
import tempfile

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# Default video settings
FPS = 24


# -------------------------
# REQUEST SCHEMA
# -------------------------
class GenerateVideoRequest(BaseModel):
    image: str | None = None
    reference_image: str | None = None
    prompt: str | None = "cinematic motion"
    duration: int | None = 3
    mode: str | None = "cinematic"


# -------------------------
# HEALTH CHECK (CRITICAL)
# -------------------------
@app.get("/ping")
def ping():
    return {"ok": True}


# -------------------------
# HELPERS
# -------------------------
def decode_image(b64_or_data_url: str):
    if "," in b64_or_data_url:
        b64_or_data_url = b64_or_data_url.split(",")[1]

    img_bytes = base64.b64decode(b64_or_data_url)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image input")

    return img


def make_video(frame, prompt: str, duration: int):
    height, width = frame.shape[:2]
    total_frames = FPS * max(duration, 1)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, FPS, (width, height))

        if not writer.isOpened():
            raise RuntimeError("Failed to initialize video writer")

        safe_prompt = (prompt or "cinematic")[:80]

        for i in range(total_frames):
            t = i / max(total_frames - 1, 1)

            # Zoom effect
            zoom = 1.0 + 0.1 * np.sin(t * np.pi)
            nh, nw = int(height / zoom), int(width / zoom)
            y = (height - nh) // 2
            x = (width - nw) // 2

            cropped = frame[y:y+nh, x:x+nw]
            resized = cv2.resize(cropped, (width, height))

            # Text overlay
            cv2.putText(
                resized,
                safe_prompt,
                (20, height - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            writer.write(resized)

        writer.release()

        with open(out_path, "rb") as f:
            return f.read()


# -------------------------
# MAIN GENERATION ROUTE
# -------------------------
@app.post("/generate-video")
def generate_video(payload: GenerateVideoRequest):
    try:
        image_b64 = payload.reference_image or payload.image
        if not image_b64:
            raise HTTPException(status_code=400, detail="No image provided")

        frame = decode_image(image_b64)
        video_bytes = make_video(
            frame,
            payload.prompt or "",
            payload.duration or 3
        )

        video_b64 = base64.b64encode(video_bytes).decode("utf-8")

        return JSONResponse({
            "status": "COMPLETED",
            "output": {
                "video_b64": video_b64,
                "mime_type": "video/mp4",
                "filename": "out.mp4"
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "FAILED",
                "error": str(e)
            }
        )


# -------------------------
# START SERVER
# -------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
