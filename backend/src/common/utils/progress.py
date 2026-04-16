from collections.abc import Iterable, Iterator


def track_progress(
    items: Iterable,
    total: int | None = None,
    description: str = "Выполнение",
) -> Iterator:
    """Wrap an iterable with a console progress bar."""
    from tqdm import tqdm

    return tqdm(items, total=total, desc=description, unit="item")
