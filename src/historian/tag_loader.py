import yaml
from pathlib import Path
from typing import List

from .models import TagConfig


def load_tags(path: str) -> List[TagConfig]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Tags file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    tags = []

    for entry in data.get("tags", []):
        tags.append(
            TagConfig(
                name=entry["name"],
                type=entry["type"],
                address=entry["address"],
                unit=entry.get("unit", 1),
                byteorder=entry.get("byteorder", "big"),
                scale=entry.get("scale"),
            )
        )

    return tags