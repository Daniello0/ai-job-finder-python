"""Sentence-BERT vacancy embedding settings (see docs/design.mdc)."""

# Multilingual MiniLM; output dimension 384 — matches PostgreSQL vector(384).
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

DEFAULT_EMBED_BATCH_SIZE = 32

# Top-K semantic matches (see docs/design.mdc — «top 5 most relevant»).
DEFAULT_SIMILARITY_TOP_K = 5

# --- Weighted text for vacancy → vector (bi-encoder / mean pooling) ---
# Long boilerplate descriptions (e.g. retail chains) often hurt retrieval: they add many
# tokens and dilute title / employment / schedule under mean pooling. Default: do not embed
# the free-text description; rely on structured fields + title + skills.
VACANCY_EMBED_INCLUDE_DESCRIPTION = True

# When VACANCY_EMBED_INCLUDE_DESCRIPTION is True: None = full text; int = soft cap (chars).
VACANCY_EMBED_DESCRIPTION_MAX_CHARS: int | None = None

# More repetitions ⇒ more tokens from that field ⇒ stronger influence under mean pooling.
VACANCY_EMBED_TITLE_REPEATS = 4
VACANCY_EMBED_STRUCTURE_REPEATS = 3
VACANCY_EMBED_COMPANY_REPEATS = 1
VACANCY_EMBED_SKILLS_REPEATS = 1
