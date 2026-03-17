# database.py
import databases
import sqlalchemy
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Async database instance — used for all queries
database = databases.Database(DATABASE_URL)

# SQLAlchemy engine — used for table reflection only
engine = sqlalchemy.create_engine(DATABASE_URL)