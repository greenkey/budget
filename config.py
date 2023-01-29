import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

ROOT_FOLDER = Path(__file__).parent
DATA_FOLDER = ROOT_FOLDER / os.getenv("DATA_FOLDER", "data")
DB_PATH = ROOT_FOLDER / os.getenv("DB_PATH", "data/budget.db")
