# backend/app/main.py
from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.api import ubid, sws, fds, propagation
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Samanvaya – Government Interoperability Layer",
    description="Bidirectional sync between SWS and FDS via UBID",
    version="2.0.0",
)

# Open CORS so the frontend HTML file can call the API
# regardless of whether it's served from file://, localhost:3000, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully.")
    except OperationalError as e:
        logger.error("Database connection failed: %s", e)


# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(ubid.router)
app.include_router(sws.router)
app.include_router(fds.router)
app.include_router(propagation.router)


@app.get("/")
def root():
    return {
        "service": "Samanvaya Interoperability Layer",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
