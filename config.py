import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_FOLDER = Path(__file__).parent
DATA_FOLDER = ROOT_FOLDER / os.getenv("DATA_FOLDER", "data")
DB_PATH = ROOT_FOLDER / os.getenv("DB_PATH", "data/budget.db")
MODEL_FOLDER = ROOT_FOLDER / os.getenv("MODEL_FOLDER", "models")

GSHEET_SHEET_ID = os.getenv("GSHEET_SHEET_ID")
GSHEET_CREDENTIALS = ROOT_FOLDER / os.getenv("GSHEET_CREDENTIALS", "credentials.json")
