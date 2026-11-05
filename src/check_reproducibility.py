
"""Calculate SHA-256 hashes of the generated analysis files."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

files = [
    DATA / "steam_games.csv",
    DATA / "steam_genres.csv",
    DATA / "steam_tags.csv",
    DATA / "steam_publishers.csv",
    DATA / "steam_release_dates.csv",
]

files.extend(
    sorted((DATA / "analysis").glob("*.csv"))
)

print("\nFILE HASHES")
print("-" * 60)

for path in files:
    if path.exists():
        digest = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        print(f"{path.name}: {digest}")
    else:
        print(f"Missing: {path.name}")
