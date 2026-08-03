"""Valide un snapshot JSON avant publication."""

import json
import sys
from pathlib import Path

from snapshot_contract import validate_snapshot


def main(path="snapshot.json"):
    snapshot_path = Path(path)
    with snapshot_path.open(encoding="utf-8") as handle:
        validate_snapshot(json.load(handle))
    print(f"OK — contrat snapshot valide : {snapshot_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "snapshot.json")
