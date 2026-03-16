from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="ShopSense API",
    description="Backend for ShopSense e-commerce analytics platform",
    version="1.0.0"
)

# CORS — allows your Next.js frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",           # Local Next.js dev server
        os.getenv("FRONTEND_URL", ""),     # Production Vercel URL (added later)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ShopSense API is running"}

@app.get("/")
def root():
    return {"message": "Welcome to ShopSense API"}