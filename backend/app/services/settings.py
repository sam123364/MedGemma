from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("ASTRA_DB_PATH", str(DATA_DIR / "astra.db")))
CHROMA_PATH = Path(os.getenv("ASTRA_CHROMA_PATH", str(DATA_DIR / "chroma")))

MEDGEMMA_RUNTIME = os.getenv("MEDGEMMA_RUNTIME", "mock")
MEDGEMMA_MODEL = os.getenv("MEDGEMMA_MODEL", "google/medgemma-27b-it")
MEDGEMMA_MLX_ENDPOINT = os.getenv("MEDGEMMA_MLX_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
MEDGEMMA_OLLAMA_URL = os.getenv("MEDGEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MEDGEMMA_OLLAMA_MODEL = os.getenv("MEDGEMMA_OLLAMA_MODEL", "medgemma")

SIM_HORIZON_DAYS = int(os.getenv("SIM_HORIZON_DAYS", "180"))
COARSE_TRIALS = int(os.getenv("COARSE_TRIALS", "1000"))
HIGH_FIDELITY_COUNT = int(os.getenv("HIGH_FIDELITY_COUNT", "5"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

