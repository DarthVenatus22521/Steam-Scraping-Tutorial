"""Offline cleaning and normalization of cached Steam game data."""

import json
from pathlib import Path

import pandas as pd

from analysis_utils import parse_genres, parse_tags, make_publishers_table


def load_and_prepare_data(data_dir: Path):
    """Read local sources, clean games, build related genre/tag/publisher tables."""
    DATA = Path(data_dir)
    df = pd.read_csv(DATA / "steam_games_raw.csv")

    print(f"Raw dataset: {len(df):,} games")

    # Merge locally collected release dates
    release_path = DATA / "steam_release_dates.csv"

    if release_path.exists():
        release_df = pd.read_csv(
            release_path,
            usecols=["appid", "release_date", "release_year"]
        )

        release_df["appid"] = pd.to_numeric(
            release_df["appid"], errors="coerce"
        )

        release_df = release_df.drop_duplicates("appid")

        df = df.merge(
            release_df,
            on="appid",
            how="left",
            validate="one_to_one"
        )

        df["release_date"] = pd.to_datetime(
            df["release_date"],
            errors="coerce"
        )

        print(
            "Release dates matched:",
            df["release_date"].notna().sum()
        )
    else:
        df["release_date"] = pd.NaT
        df["release_year"] = pd.NA
        print("Release-date lookup not found.")

    columns = [
        "appid",
        "name",
        "release_date",
        "release_year",
        "developer",
        "publisher",
        "positive",
        "negative",
        "price",
        "initialprice",
        "discount",
        "owners",
        "genre",
        "tags",
        "languages",
        "ccu"
    ]

    df = df.reindex(columns=columns)

    numeric_columns = [
        "appid",
        "positive",
        "negative",
        "price",
        "initialprice",
        "discount",
        "ccu"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = df.dropna(subset=["appid"])
    df["appid"] = df["appid"].astype(int)
    df = df.drop_duplicates(subset="appid")

    df["total_reviews"] = (
        df["positive"] + df["negative"]
    )

    df["positive_pct"] = (
        100 * df["positive"] /
        df["total_reviews"].replace(0, float("nan"))
    )

    df["price_usd"] = df["price"] / 100
    df["original_price_usd"] = df["initialprice"] / 100

    df["free_to_play"] = (
        df["original_price_usd"] == 0
    )

    # Price brackets, using original prices
    price_bins = [-0.01, 0, 5, 10, 20, 40, float("inf")]
    price_labels = [
        "Free",
        "$0.01–$5",
        "$5.01–$10",
        "$10.01–$20",
        "$20.01–$40",
        "Over $40"
    ]

    df["price_category"] = pd.cut(
        df["original_price_usd"],
        bins=price_bins,
        labels=price_labels
    )

    df["genre_list"] = df["genre"].apply(parse_genres)

    df["genre_count"] = df["genre_list"].apply(len)

    df["tag_dict"] = df["tags"].apply(parse_tags)

    df["tag_count"] = df["tag_dict"].apply(len)

    # Store lists/dictionaries as JSON for CSV compatibility
    df["genres_json"] = df["genre_list"].apply(json.dumps)
    df["tags_json"] = df["tag_dict"].apply(json.dumps)

    df = df.dropna(
        subset=[
            "price_usd",
            "original_price_usd",
            "positive_pct"
        ]
    )

    df = df[
        (df["price_usd"] >= 0) &
        (df["original_price_usd"] >= 0) &
        (df["total_reviews"] >= 50)
    ].copy()

    print(f"Cleaned dataset: {len(df):,} games")

    genres_df = (
        df[[
            "appid",
            "name",
            "positive_pct",
            "total_reviews",
            "original_price_usd",
            "genre_list"
        ]]
        .explode("genre_list")
        .rename(columns={"genre_list": "genre"})
    )

    genres_df = genres_df.dropna(subset=["genre"])

    # ---------------------------------
    # 9A. Create a tag-level dataset
    # ---------------------------------

    tag_records = []

    for game in df.itertuples():
        for tag, votes in game.tag_dict.items():
            tag_records.append({
                "appid": game.appid,
                "name": game.name,
                "tag": tag,
                "tag_votes": votes,
                "positive_pct": game.positive_pct,
                "total_reviews": game.total_reviews,
                "original_price_usd": game.original_price_usd
            })

    tags_df = pd.DataFrame(
        tag_records,
        columns=[
            "appid",
            "name",
            "tag",
            "tag_votes",
            "positive_pct",
            "total_reviews",
            "original_price_usd"
        ]
    )

    tags_df["tag_votes"] = pd.to_numeric(
        tags_df["tag_votes"],
        errors="coerce"
    )

    # ---------------------------------
    # 9B. Create a normalized publisher table
    # ---------------------------------

    publishers_df = make_publishers_table(df)

    publishers_df.to_csv(
        DATA / "steam_publishers.csv",
        index=False
    )

    print("\nPUBLISHER NORMALIZATION")

    print(
        "Game-publisher relationships:",
        len(publishers_df)
    )

    print(
        "Unique publisher names:",
        publishers_df["publisher"].nunique()
    )

    print(
        "Games with multiple publishers:",
        publishers_df.groupby("appid")
        .size()
        .gt(1)
        .sum()
    )

    print(
        "Duplicate game-publisher pairs:",
        publishers_df.duplicated(
            subset=["appid", "publisher"]
        ).sum()
    )

    # Inspect original publisher labels that
    # were separated into multiple publishers
    multi_publisher_games = publishers_df[
        publishers_df["publisher_count"] > 1
    ]

    print("\nEXAMPLE MULTI-PUBLISHER LABELS")

    print(
        multi_publisher_games[
            ["original_publisher", "publisher"]
        ]
        .drop_duplicates()
        .head(20)
        .to_string(index=False)
    )
    return df, genres_df, tags_df, publishers_df


def save_cleaned_tables(df, genres_df, tags_df, data_dir: Path):
    """Export game, genre, and tag CSVs without acquiring remote data."""
    DATA = Path(data_dir)
    games_output = df.drop(
        columns=["genre_list", "tag_dict", "tags"]
    )

    games_output.to_csv(
        DATA / "steam_games.csv", index=False
    )

    genres_df.to_csv(
        DATA / "steam_genres.csv", index=False
    )

    tags_df.to_csv(
        DATA / "steam_tags.csv", index=False
    )

    print("\nDataset sizes:")
    print(f"Games: {len(df):,}")
    print(f"Game-genre combinations: {len(genres_df):,}")
    print(f"Game-tag combinations: {len(tags_df):,}")


def validate_data(df, genres_df, tags_df, publishers_df):
    """Print original data validation checks."""
    print("\nDATA VALIDATION")

    print("Unique game IDs:",
          df["appid"].nunique())

    print("Games without genres:",
          (df["genre_count"] == 0).sum())

    print("Games without tags:",
          (df["tag_count"] == 0).sum())

    print("Duplicate game-genre pairs:",
          genres_df.duplicated(
              subset=["appid", "genre"]
          ).sum())

    print("Duplicate game-tag pairs:",
          tags_df.duplicated(
              subset=["appid", "tag"]
          ).sum())

    print("Ratings outside 0–100:",
          (~df["positive_pct"].between(0, 100)).sum())

    print("Negative prices:",
          (df["original_price_usd"] < 0).sum())


    # Additional validation: publishers and release dates

    print("Duplicate game-publisher pairs:",
          publishers_df.duplicated(
              subset=["appid", "publisher"]
          ).sum())

    print("Games with release dates:",
          df["release_date"].notna().sum())

    print("Games missing release dates:",
          df["release_date"].isna().sum())

    print("Release years before 1990:",
          (
              pd.to_numeric(df["release_year"], errors="coerce")
              < 1990
          ).sum())

    print("Release years after 2026:",
          (
              pd.to_numeric(df["release_year"], errors="coerce")
              > 2026
          ).sum())


def print_data_summary(df, genres_df, tags_df):
    """Report dataset statistics."""
    print("\nGame summary statistics:")
    print(
        df[[
            "original_price_usd",
            "positive_pct",
            "total_reviews",
            "genre_count",
            "tag_count"
        ]].describe().round(2)
    )

    print("\nMost common genres:")
    print(genres_df["genre"].value_counts().head(15))

    print("\nMost common tags:")
    print(tags_df["tag"].value_counts().head(20))

    print("\nGames by price category:")
    print(df["price_category"].value_counts().sort_index())


