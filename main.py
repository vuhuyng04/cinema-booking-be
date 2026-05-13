"""Cinema Booking BE — FastAPI on Render."""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import bookings, admin  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CineBook API", version="1.0.0", lifespan=lifespan)

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "*")
allowed = [o.strip() for o in frontend_origin.split(",")] if frontend_origin != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"name": "CineBook API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(bookings.router)
app.include_router(admin.router)
