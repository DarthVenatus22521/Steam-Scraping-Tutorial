
"""Collect Steam release dates from The Game Census.

Source: https://thegamecensus.com/data
License: CC BY 4.0 (attribution required)

Run separately from main.py:
    uv run python src/collect_release_dates.py
"""

from pathlib import Path
from datetime import datetime, timezone
import io

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"

RAW.mkdir(parents=True, exist_ok=True)

SOURCE_URL = "https://thegamecensus.com/data/games-index.csv"

SOURCE_CACHE = RAW / "game_census_index.csv"
OUTPUT = DATA / "steam_release_dates.csv"


def download_source(refresh=False):
    """Download once, or reuse the local cached source."""
    if SOURCE_CACHE.exists() and not refresh:
        print("Using cached Game Census data.")
        return SOURCE_CACHE

    print("Downloading Game Census index...", flush=True)

    response = requests.get(
        SOURCE_URL,
        timeout=120,
        headers={"User-Agent": "SteamGameAnalysis/1.0"}
    )
    response.raise_for_status()

    # Validate the file before replacing the cache
    contents = response.content
    test = pd.read_csv(io.BytesIO(contents), nrows=5)

    required = {"app_id", "release_date"}
    if not required.issubset(test.columns):
        raise ValueError(
            f"Missing expected columns: {required - set(test.columns)}"
        )

    temporary = SOURCE_CACHE.with_suffix(".tmp")
    temporary.write_bytes(contents)
    temporary.replace(SOURCE_CACHE)

    return SOURCE_CACHE


def build_release_lookup(source_path):
    """Match downloaded release dates to our original games."""
    games = pd.read_csv(
        DATA / "steam_games_raw.csv",
        usecols=["appid"]
    )

    dates = pd.read_csv(
        source_path,
        usecols=["app_id", "release_date"]
    )

    games["appid"] = pd.to_numeric(
        games["appid"], errors="coerce"
    ).astype("Int64")

    dates["app_id"] = pd.to_numeric(
        dates["app_id"], errors="coerce"
    ).astype("Int64")

    dates = dates.rename(columns={"app_id": "appid"})
    dates = dates.dropna(subset=["appid"])
    dates = dates.drop_duplicates("appid")

    dates["release_date"] = pd.to_datetime(
        dates["release_date"],
        errors="coerce",
        format="%Y-%m-%d"
    )

    result = (
        games[["appid"]]
        .dropna()
        .drop_duplicates()
        .merge(
            dates,
            on="appid",
            how="left",
            validate="one_to_one"
        )
    )

    result["release_year"] = (
        result["release_date"].dt.year.astype("Int64")
    )

    result["release_source"] = (
        "The Game Census"
    )

    result["retrieved_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    result.to_csv(OUTPUT, index=False)

    matched = result["release_date"].notna().sum()

    print(f"\nGames checked: {len(result):,}")
    print(f"Release dates found: {matched:,}")
    print(f"Missing dates: {len(result) - matched:,}")
    print(f"Coverage: {matched / len(result):.1%}")
    print(f"Saved to: {OUTPUT}")


def main():
    source_path = download_source()
    build_release_lookup(source_path)


if __name__ == "__main__":
    main()
