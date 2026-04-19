"""Shared Sentence-BERT encoding (used by vector ingestion and similarity search)."""

from __future__ import annotations

import asyncio
from typing import Any

from common.constants.embedding import (
    DEFAULT_EMBED_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
)
from features.database.models import Vector

_model: Any = None


def require_pgvector_embedding() -> None:
    """Ensure ORM was built with pgvector (Vector column), not Text fallback."""
    if Vector is None:
        msg = (
            "pgvector is required: install pgvector and use PostgreSQL for embeddings."
        )
        raise RuntimeError(msg)


def _torch_major_minor(version: str) -> tuple[int, int]:
    core = version.split("+", 1)[0].strip().split(".")[:2]
    return int(core[0]), int(core[1])


def _require_torch_for_embeddings() -> None:
    """sentence-transformers needs a working PyTorch 2.x (see backend/requirements.txt pins)."""
    try:
        import torch
    except ModuleNotFoundError as err:
        msg = "Install PyTorch 2.x: `pip install torch` (see backend/requirements.txt)."
        raise RuntimeError(msg) from err
    if _torch_major_minor(torch.__version__) < (2, 0):
        msg = f"PyTorch 2.x is required for Sentence-BERT (found {torch.__version__})."
        raise RuntimeError(msg)


def _get_sentence_transformer() -> Any:
    global _model
    if _model is None:
        _require_torch_for_embeddings()
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as err:
            msg = (
                "Install sentence-transformers in this Python environment, e.g. "
                "`pip install sentence-transformers` or `pip install -r backend/requirements.txt`."
            )
            raise RuntimeError(msg) from err

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


async def encode_texts(texts: list[str]) -> list[list[float]]:
    """Run Sentence-BERT encoding off the asyncio event loop."""

    def _encode() -> Any:
        st = _get_sentence_transformer()
        return st.encode(
            texts,
            batch_size=min(len(texts), DEFAULT_EMBED_BATCH_SIZE),
            show_progress_bar=False,
        )

    arr = await asyncio.to_thread(_encode)
    return [arr[i].tolist() for i in range(len(texts))]
