import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "selfies"


@router.post("/selfie")
async def upload_selfie(image: UploadFile = File(...)):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = UPLOAD_DIR / filename
    contents = await image.read()
    path.write_bytes(contents)
    return {"url": f"/uploads/selfies/{filename}"}
