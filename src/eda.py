"""Analytical summaries from locally curated Steam game data."""

from pathlib import Path
import pandas as pd

from analysis_utils import summarize_publishers


def analyze_prices(df):
    """Compute ratings by original price bracket."""
    price_summary = (
        df.groupby(
            "price_category",
            observed=True
        )
        .agg(
            games=("appid", "count"),
            mean_rating=("positive_pct", "mean"),
            median_rating=("positive_pct", "median"),
            mean_reviews=("total_reviews", "mean")
        )
        .round(2)
    )

    print("\nRATINGS BY PRICE CATEGORY")
    print(price_summary)
    return price_summary


def analyze_correlations(df):
    """Compare paid-game price with positive-review percentage."""
    paid_games = df[
        df["original_price_usd"] > 0
    ].copy()

    pearson_corr = paid_games[
        "original_price_usd"
    ].corr(
        paid_games["positive_pct"],
        method="pearson"
    )

    spearman_corr = paid_games[
        "original_price_usd"
    ].corr(
        paid_games["positive_pct"],
        method="spearman"
    )

    print("\nPRICE VS. RATING CORRELATIONS")
    print(f"Paid games analyzed: {len(paid_games):,}")
    print(f"Pearson correlation: {pearson_corr:.3f}")
    print(f"Spearman correlation: {spearman_corr:.3f}")


def analyze_genre_prices(df, genres_df):
    """Compare median game ratings across genre-price groups."""
    # Select genres with at least 500 games
    major_genres = (
        genres_df["genre"]
        .value_counts()
        .loc[lambda x: x >= 500]
        .index
    )

    # Include the game's price category
    genre_price = genres_df.merge(
        df[["appid", "price_category"]],
        on="appid",
        how="left",
        validate="many_to_one"
    )

    genre_price = genre_price[
        genre_price["genre"].isin(major_genres)
    ].copy()

    # Calculate median rating by genre and price
    genre_price_summary = (
        genre_price
        .groupby(
            ["genre", "price_category"],
            observed=True
        )
        .agg(
            games=("appid", "nunique"),
            median_rating=("positive_pct", "median")
        )
        .reset_index()
    )

    print("\nGENRE AND PRICE CATEGORY SUMMARY")
    print(genre_price_summary.to_string(index=False))
    return genre_price_summary


def analyze_tags(df, tags_df):
    """Summarize frequent tags and tagged-versus-untagged rating differences."""
    MIN_TAG_GAMES = 100

    # One game-tag combination per row
    tag_summary = (
        tags_df
        .groupby("tag")
        .agg(
            games=("appid", "nunique"),
            mean_rating=("positive_pct", "mean"),
            median_rating=("positive_pct", "median"),
            median_tag_votes=("tag_votes", "median")
        )
        .reset_index()
    )

    # Restrict to tags with substantial representation
    tag_summary = tag_summary[
        tag_summary["games"] >= MIN_TAG_GAMES
    ].copy()

    # Compare tagged games against games without that tag
    total_games = len(df)
    total_rating_sum = df["positive_pct"].sum()

    tag_rating_sums = (
        tags_df.groupby("tag")["positive_pct"]
        .sum()
    )

    tag_summary["without_tag_games"] = (
        total_games - tag_summary["games"]
    )

    tag_summary["mean_without_tag"] = (
        total_rating_sum
        - tag_summary["tag"].map(tag_rating_sums)
    ) / tag_summary["without_tag_games"]

    tag_summary["rating_difference"] = (
        tag_summary["mean_rating"]
        - tag_summary["mean_without_tag"]
    )

    tag_summary = tag_summary.round(2)

    # Highest-rated tags
    highest_tags = (
        tag_summary
        .sort_values("median_rating", ascending=False)
        .head(15)
    )

    print("\n15 HIGHEST-RATED COMMUNITY TAGS")
    print(
        highest_tags[
            ["tag", "games", "mean_rating", "median_rating"]
        ].to_string(index=False)
    )

    # Lowest-rated tags
    lowest_tags = (
        tag_summary
        .sort_values("median_rating")
        .head(15)
    )

    print("\n15 LOWEST-RATED COMMUNITY TAGS")
    print(
        lowest_tags[
            ["tag", "games", "mean_rating", "median_rating"]
        ].to_string(index=False)
    )

    # Largest positive differences
    positive_tags = (
        tag_summary
        .sort_values("rating_difference", ascending=False)
        .head(15)
    )

    print("\nTAGS WITH LARGEST POSITIVE RATING DIFFERENCES")
    print(
        positive_tags[
            [
                "tag",
                "games",
                "mean_rating",
                "mean_without_tag",
                "rating_difference"
            ]
        ].to_string(index=False)
    )

    # Largest negative differences
    negative_tags = (
        tag_summary
        .sort_values("rating_difference")
        .head(15)
    )

    print("\nTAGS WITH LARGEST NEGATIVE RATING DIFFERENCES")
    print(
        negative_tags[
            [
                "tag",
                "games",
                "mean_rating",
                "mean_without_tag",
                "rating_difference"
            ]
        ].to_string(index=False)
    )
    return tag_summary


def analyze_publishers(publishers_df):
    """Summarize normalized publisher relationships."""
    MIN_PUBLISHER_GAMES = 10

    publisher_summary = summarize_publishers(
        publishers_df,
        minimum_games=MIN_PUBLISHER_GAMES
    )

    print("\nNORMALIZED PUBLISHER ANALYSIS")

    print("Publishers with at least 10 games:",
          len(publisher_summary))

    print("\n15 HIGHEST-RATED PUBLISHERS")
    print(
        publisher_summary
        .head(15)
        .round(2)
        .to_string(index=False)
    )

    print("\n15 LOWEST-RATED PUBLISHERS")
    print(
        publisher_summary
        .tail(15)
        .iloc[::-1]
        .round(2)
        .to_string(index=False)
    )
    return publisher_summary


def analyze_sensitivity(df):
    """Assess sensitivity to minimum review-count requirements."""
    REVIEW_THRESHOLDS = [50, 500, 2000]

    sensitivity_records = []
    sensitivity_price_records = []

    for minimum_reviews in REVIEW_THRESHOLDS:

        subset = df[
            df["total_reviews"] >= minimum_reviews
        ].copy()

        # Overall sample statistics
        sensitivity_records.append({
            "minimum_reviews": minimum_reviews,
            "games": len(subset),
            "mean_rating": subset["positive_pct"].mean(),
            "median_rating": subset["positive_pct"].median()
        })

        # Rating summaries across price categories
        category_summary = (
            subset
            .groupby("price_category", observed=True)
            .agg(
                games=("appid", "nunique"),
                mean_rating=("positive_pct", "mean"),
                median_rating=("positive_pct", "median")
            )
            .reset_index()
        )

        category_summary["minimum_reviews"] = minimum_reviews

        sensitivity_price_records.append(category_summary)

    sensitivity_summary = pd.DataFrame(
        sensitivity_records
    ).round(2)

    sensitivity_price_summary = pd.concat(
        sensitivity_price_records,
        ignore_index=True
    ).round(2)

    print("\nSENSITIVITY ANALYSIS")
    print(sensitivity_summary.to_string(index=False))

    print("\nPRICE CATEGORY SENSITIVITY")

    print(
        sensitivity_price_summary[
            [
                "minimum_reviews",
                "price_category",
                "games",
                "mean_rating",
                "median_rating"
            ]
        ].to_string(index=False)
    )

    # Correlations under different review thresholds
    print("\nCORRELATIONS BY REVIEW THRESHOLD")

    for minimum_reviews in REVIEW_THRESHOLDS:

        subset = df[
            (df["total_reviews"] >= minimum_reviews) &
            (df["original_price_usd"] > 0)
        ]

        pearson = subset["original_price_usd"].corr(
            subset["positive_pct"],
            method="pearson"
        )

        spearman = subset["original_price_usd"].corr(
            subset["positive_pct"],
            method="spearman"
        )

        print(
            f"Minimum {minimum_reviews:,} reviews | "
            f"Games: {len(subset):,} | "
            f"Pearson: {pearson:.3f} | "
            f"Spearman: {spearman:.3f}"
        )
    return sensitivity_summary, sensitivity_price_summary


def analyze_release_year(df):
    """Summarize rating by historical release year."""
    release_games = df.copy()

    release_games["release_year"] = pd.to_numeric(
        release_games["release_year"],
        errors="coerce"
    )

    # Exclude missing and future release dates
    # CURRENT_YEAR = pd.Timestamp.today().year
    CURRENT_YEAR = 2026

    release_games = release_games[
        release_games["release_year"].notna() &
        release_games["release_year"].between(
            1990, CURRENT_YEAR
        )
    ].copy()

    year_summary = (
        release_games
        .groupby("release_year")
        .agg(
            games=("appid", "nunique"),
            mean_rating=("positive_pct", "mean"),
            median_rating=("positive_pct", "median"),
            median_price=("original_price_usd", "median"),
            median_reviews=("total_reviews", "median")
        )
        .reset_index()
    )

    # Avoid drawing conclusions from tiny year groups
    year_plot = year_summary[
        year_summary["games"] >= 20
    ].copy()

    print("\nRELEASE YEAR ANALYSIS")
    print(f"Games with usable release dates: {len(release_games):,}")

    print(
        year_summary
        .round(2)
        .to_string(index=False)
    )
    return year_summary, year_plot


def export_analysis_results(data_dir: Path, figures_dir: Path, price_summary, genre_price_summary, tag_summary, publisher_summary, sensitivity_summary, sensitivity_price_summary, year_summary):
    """Write original analytical CSV summaries in the same format."""
    DATA = Path(data_dir)
    FIGURES = Path(figures_dir)
    ANALYSIS_DIR = DATA / "analysis"
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Price analysis
    price_summary.to_csv(
        ANALYSIS_DIR / "price_summary.csv"
    )

    # Genre and price analysis
    genre_price_summary.to_csv(
        ANALYSIS_DIR / "genre_price_summary.csv",
        index=False
    )

    # Community tag analysis
    tag_summary.to_csv(
        ANALYSIS_DIR / "tag_summary.csv",
        index=False
    )

    # Publisher analysis
    publisher_summary.to_csv(
        ANALYSIS_DIR / "publisher_summary.csv",
        index=False
    )

    # Sensitivity analysis
    sensitivity_summary.to_csv(
        ANALYSIS_DIR / "sensitivity_summary.csv",
        index=False
    )

    sensitivity_price_summary.to_csv(
        ANALYSIS_DIR / "sensitivity_price_summary.csv",
        index=False
    )

    print("\nANALYSIS COMPLETE")
    print(f"Analysis tables saved to: {ANALYSIS_DIR}")
    print(f"Figures saved to: {FIGURES}")
    year_summary.to_csv(
        ANALYSIS_DIR / "release_year_summary.csv",
        index=False
    )


