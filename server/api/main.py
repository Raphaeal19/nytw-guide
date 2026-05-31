from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api.routes import events, people, ingest, met, outreach


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


@app.get("/health")
def health():
    return {"status": "ok"}
