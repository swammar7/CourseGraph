"""Local-only embedding model wrapper, loaded lazily on first use."""
from __future__ import annotations

import os
from pathlib import Path


class LocalEmbedder:
    def __init__(self, model_dir: str | Path = "models/all-MiniLM-L6-v2") -> None:
        self.model_dir = Path(model_dir)
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not self.model_dir.is_dir():
                raise RuntimeError(
                    f"Yerel embedding modeli bulunamadı: {self.model_dir}. "
                    "Önce 'python prepare_model.py' komutunu çalıştırın."
                )
            # Prevent an accidental network fallback during actual PDF processing.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(str(self.model_dir), local_files_only=True)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        arrays = self._get_model().encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [[float(v) for v in vector] for vector in arrays]
