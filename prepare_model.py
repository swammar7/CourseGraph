"""One-time, explicit model download; never upload PDF data to a service."""
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TARGET = Path("models/all-MiniLM-L6-v2")

if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    SentenceTransformer(MODEL).save(str(TARGET))
    print(f"Model hazır: {TARGET.resolve()}")
