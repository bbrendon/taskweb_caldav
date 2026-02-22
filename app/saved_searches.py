import json
import uuid
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "saved_searches.json"


def load() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text())


def save(name: str, query: str) -> dict:
    searches = load()
    entry = {"id": str(uuid.uuid4()), "name": name, "query": query}
    searches.append(entry)
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(searches, indent=2))
    return entry


def delete(id: str) -> bool:
    searches = load()
    new = [s for s in searches if s["id"] != id]
    if len(new) == len(searches):
        return False
    DATA_FILE.write_text(json.dumps(new, indent=2))
    return True
