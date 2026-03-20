# database.py
import databases
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Async database instance — used for all queries
# min_size/max_size limits connections on free tier
database = databases.Database(
    DATABASE_URL,
    min_size=1,
    max_size=3,
)