from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


class FakeEmbedder:
    """Deterministic, offline, tiny embedding vectors for E1 unit tests."""

    def __init__(self):
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        return [[float(len(text)), 1.0, 0.25] for text in texts]


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def sample_pdf():
    return (Path(__file__).parent / "fixtures" / "two_pages.pdf").read_bytes()
