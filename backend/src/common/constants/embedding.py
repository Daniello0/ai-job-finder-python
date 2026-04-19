"""Sentence-BERT vacancy embedding settings (see docs/design.mdc)."""

# Multilingual MiniLM; output dimension 384 — matches PostgreSQL vector(384).
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

DEFAULT_EMBED_BATCH_SIZE = 32
