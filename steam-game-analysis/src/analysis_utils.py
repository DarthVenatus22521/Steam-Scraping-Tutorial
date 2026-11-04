
"""Reusable helpers for the Steam game analysis."""

import ast
import json
import re

import pandas as pd


# ---------------------------------
# Genre parsing
# ---------------------------------

def parse_genres(value):
    """Convert comma-separated genres into a list."""
    if pd.isna(value) or not str(value).strip():
        return []

    return list(dict.fromkeys(
        genre.strip()
        for genre in str(value).split(",")
        if genre.strip()
    ))


# ---------------------------------
# Community tag parsing
# ---------------------------------

def parse_tags(value):
    """Convert serialized Steam Spy tags to a dictionary."""
    if isinstance(value, dict):
        return value

    if not isinstance(value, str) or not value.strip():
        return {}

    # The collector saves tags as JSON.
    try:
        result = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        # Fallback for older Python-style dictionaries
        try:
            result = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}

    return result if isinstance(result, dict) else {}


# Corporate suffixes that contain commas
CORPORATE_SUFFIXES = (
    "Ltd.", "Ltd", "Inc.", "Inc", "LLC",
    "L.L.C.", "PLC", "Corp.", "Corporation"
)



def parse_publishers(value):
    """Split publisher lists while preserving corporate suffixes."""
    if pd.isna(value) or not str(value).strip():
        return []

    text = str(value).strip()

    # Protect commas before corporate suffixes,
    # including suffixes with regional qualifiers.
    suffix_pattern = re.compile(
        r",\s*("
        r"(?:Inc\.?|Ltd\.?|LLC|L\.L\.C\.|"
        r"PLC|Corp\.?|Corporation)"
        r"(?:\s*\([^)]*\))?"
        r")(?=\s*(?:[,;]|$))",
        flags=re.IGNORECASE
    )

    protected = suffix_pattern.sub(
        lambda match: "@@COMMA@@ " + match.group(1),
        text
    )

    pieces = re.split(r"\s*[,;]\s*", protected)

    publishers = [
        piece.replace("@@COMMA@@", ",").strip()
        for piece in pieces
        if piece.strip()
    ]

    return list(dict.fromkeys(publishers))


def make_publishers_table(games_df):
    """Create one record per game-publisher relationship."""
    records = []

    for game in games_df.itertuples():
        publishers = parse_publishers(game.publisher)

        for publisher in publishers:
            records.append({
                "appid": game.appid,
                "name": game.name,
                "publisher": publisher,
                "original_publisher": game.publisher,
                "publisher_count": len(publishers),
                "positive_pct": game.positive_pct,
                "total_reviews": game.total_reviews,
                "original_price_usd": game.original_price_usd
            })

    return pd.DataFrame(
        records,
        columns=[
            "appid",
            "name",
            "publisher",
            "original_publisher",
            "publisher_count",
            "positive_pct",
            "total_reviews",
            "original_price_usd"
        ]
    )


def summarize_publishers(publishers_df, minimum_games=10):
    """Summarize publishers with enough games for comparison."""
    summary = (
        publishers_df
        .groupby("publisher")
        .agg(
            games=("appid", "nunique"),
            mean_rating=("positive_pct", "mean"),
            median_rating=("positive_pct", "median"),
            median_price=("original_price_usd", "median"),
            total_reviews=("total_reviews", "sum")
        )
        .reset_index()
    )

    return summary[
        summary["games"] >= minimum_games
    ].sort_values(
        ["median_rating", "games"],
        ascending=[False, False]
    )
