# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database import database
from routers import auth, analytics    # ← add analytics here
import os

load_dotenv()

app = FastAPI(
    title="ShopSense API",
    description="Backend for ShopSense e-commerce analytics platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Routers
app.include_router(auth.router)
app.include_router(analytics.router)    # ← add this line

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ShopSense API is running"}