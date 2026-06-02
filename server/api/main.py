from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.api.routes import events, people, ingest, met, outreach, settings, identify, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Event Intel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(people.router)
app.include_router(ingest.router)
app.include_router(met.router)
app.include_router(outreach.router)
app.include_router(settings.router)
app.include_router(identify.router)
app.include_router(upload.router)

_uploads = Path(__file__).resolve().parent.parent / "uploads"
_uploads.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}
