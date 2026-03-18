# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database import database
from routers import auth, analytics, index, chat, products
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
    try:
        await database.connect()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(index.router)
app.include_router(chat.router)  
app.include_router(products.router)   

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ShopSense API is running"}