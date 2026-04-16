from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    """Load environment variables and run the parser pipeline."""
    load_dotenv(BACKEND_DIR / ".env")
    from features.parser.file_orchestrator import orchestrate_parser_pipeline

    orchestrate_parser_pipeline()


if __name__ == "__main__":
    main()
