"""Constants for user search orchestration and guardrails."""

DEFAULT_MIN_FILTERED_CANDIDATES = 1
DEFAULT_MAX_VALUES_PER_FILTER = 2

# These fields are treated as critical and are relaxed only after soft fields.
PROTECTED_RELAX_FILTER_KEYS = ("experience", "employment")
PROTECTED_RELAX_WEIGHT_PENALTY = 0.35
ROLE_KEYWORDS_HARD_LOCK = True

# Small cosine-distance bonus (lower is better) for domain keyword matches.
DOMAIN_BOOST_STEP = 0.03
