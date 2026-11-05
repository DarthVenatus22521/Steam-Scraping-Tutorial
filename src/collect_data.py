
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
GAMES = RAW / "games"

GAMES.mkdir(parents=True, exist_ok=True)

API_URL = "https://steamspy.com/api.php"
N_PAGES = 5
DETAIL_INTERVAL = 1.2
PAGE_INTERVAL = 61

session = requests.Session()
last_request = 0.0
last_page_request = 0.0


def request_json(params, interval):
    """Request JSON while respecting API rate limits."""
    global last_request, last_page_request

    is_page = params["request"] == "all"

    for attempt in range(5):
        now = time.monotonic()

        wait = max(0, DETAIL_INTERVAL - (now - last_request))

        if is_page:
            wait = max(
                wait,
                PAGE_INTERVAL - (now - last_page_request)
            )

        if wait:
            time.sleep(wait)

        # Record request timing before making the call
        last_request = time.monotonic()
        if is_page:
            last_page_request = last_request

        try:
            response = session.get(
                API_URL, params=params, timeout=45
            )
            response.raise_for_status()
            result = response.json()

            if not isinstance(result, dict):
                raise ValueError("Unexpected API response")

            return result

        except (
            requests.RequestException,
            ValueError
        ) as exc:
            if attempt == 4:
                raise

            delay = 10 * (2 ** attempt)
            print(f"Request failed: {exc}")
            print(f"Retrying after {delay} seconds")
            time.sleep(delay)


def save_json(path, data):
    """Atomically save JSON to avoid partial files."""
    temporary = path.with_suffix(".tmp")

    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    temporary.replace(path)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_game_list():
    """Collect the first five pages of Steam Spy."""
    all_games = {}

    for page in range(N_PAGES):
        path = RAW / f"game_list_page_{page}.json"

        if path.exists():
            page_data = load_json(path)

        elif page == 0 and (
            RAW / "game_list.json"
        ).exists():
            # Reuse your earlier first-page download
            page_data = load_json(RAW / "game_list.json")
            save_json(path, page_data)

        else:
            print(f"Downloading page {page}...", flush=True)

            page_data = request_json(
                {"request": "all", "page": page},
                PAGE_INTERVAL
            )
            save_json(path, page_data)

        all_games.update(page_data)
        print(f"Page {page}: {len(page_data)} games")

    print(f"Total unique games: {len(all_games)}")
    return all_games


def collect_details(game_list):
    """Download and cache each game's details."""
    records = []
    failures = []

    for index, appid in enumerate(game_list, start=1):
        path = GAMES / f"{appid}.json"

        try:
            if path.exists():
                game = load_json(path)
            else:
                game = request_json(
                    {
                        "request": "appdetails",
                        "appid": appid
                    },
                    DETAIL_INTERVAL
                )

                if not game.get("appid"):
                    raise ValueError("Missing App ID")

                save_json(path, game)

            records.append(game)

        except (
            requests.RequestException,
            ValueError,
            OSError
        ) as exc:
            failures.append(appid)
            print(f"Failed {appid}: {exc}")

        if index % 100 == 0:
            print(
                f"Processed {index}/{len(game_list)} "
                f"({len(records)} successful)",
                flush=True
            )

            # Save progress every 100 games
            save_csv(records)

    save_csv(records)

    if failures:
        print(f"\nFailed App IDs: {failures}")

    return records


def save_csv(records):
    """Save the assembled raw dataset."""
    if not records:
        return

    df = pd.DataFrame(records)

    # Tags are dictionaries, so store them as JSON strings
    if "tags" in df.columns:
        df["tags"] = df["tags"].apply(
            lambda x: json.dumps(x)
            if isinstance(x, dict) else x
        )

    output = DATA / "steam_games_raw.csv"
    temporary = DATA / "steam_games_raw.tmp"
    df.to_csv(temporary, index=False)
    temporary.replace(output)


def main():
    print("Starting Steam Spy data collection...\n")

    game_list = collect_game_list()
    records = collect_details(game_list)

    print("\nCollection complete!")
    print(f"Detailed game records: {len(records)}")
    print(f"Saved to: {DATA / 'steam_games_raw.csv'}")


if __name__ == "__main__":
    main()
