# main.py
import sys
import asyncio
import os

print(f"Python version: {sys.version}")
print("Starting imports...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database import database
from routers import auth, analytics, index, chat, products, importer

print("All imports successful")

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
    try:
        # 10 second timeout — prevents hanging if DB is slow
        await asyncio.wait_for(database.connect(), timeout=10.0)
        print("Database connected successfully")
    except asyncio.TimeoutError:
        print("Database connection timed out — continuing anyway")
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Don't raise — let server start even if DB connection fails
        # Individual routes will handle DB errors themselves

@app.on_event("shutdown")
async def shutdown():
    try:
        await database.disconnect()
    except Exception:
        pass

app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(index.router)
app.include_router(chat.router)
app.include_router(products.router)
app.include_router(importer.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ShopSense API is running"}