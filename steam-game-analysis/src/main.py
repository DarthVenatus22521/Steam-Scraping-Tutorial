
import json
import ast
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from analysis_utils import (
    parse_genres,
    parse_tags,
    make_publishers_table,
    summarize_publishers
)

# ---------------------------------
# 1. Project directories
# ---------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"

FIGURES.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")


# ---------------------------------
# 2. Load local dataset and release dates
# ---------------------------------

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


# ---------------------------------
# 3. Select columns and clean types
# ---------------------------------

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

# ---------------------------------
# 4. Feature engineering
# ---------------------------------

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

# ---------------------------------
# 5. Parse ALL genres
# ---------------------------------

df["genre_list"] = df["genre"].apply(parse_genres)

df["genre_count"] = df["genre_list"].apply(len)

# ---------------------------------
# 6. Parse ALL community tags
# ---------------------------------

df["tag_dict"] = df["tags"].apply(parse_tags)

df["tag_count"] = df["tag_dict"].apply(len)

# Store lists/dictionaries as JSON for CSV compatibility
df["genres_json"] = df["genre_list"].apply(json.dumps)
df["tags_json"] = df["tag_dict"].apply(json.dumps)

# ---------------------------------
# 7. Clean the dataset
# ---------------------------------

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

# ---------------------------------
# 8. Create a genre-level dataset
# ---------------------------------

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
# 9. Create tag and publisher datasets
# ---------------------------------

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


# ---------------------------------
# 10. Save all three datasets
# ---------------------------------

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



# ---------------------------------
# 11. Data validation
# ---------------------------------

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

# ---------------------------------
# 12. Summary statistics
# ---------------------------------

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

# ---------------------------------
# 13. Figure 1: Price vs. rating
# ---------------------------------

plt.figure(figsize=(11, 7))

sns.scatterplot(
    data=df,
    x="original_price_usd",
    y="positive_pct",
    alpha=0.25,
    s=25
)

plt.title("Steam Game Price vs. Positive Review Percentage")
plt.xlabel("Original Price (USD)")
plt.ylabel("Positive Reviews (%)")

plt.tight_layout()
plt.savefig(
    FIGURES / "price_vs_rating.png", dpi=300
)
plt.show()

# ---------------------------------
# 14. Figure 2: Ratings by genre
# ---------------------------------

top_genres = (
    genres_df["genre"]
    .value_counts()
    .head(10)
    .index
)

genre_plot = genres_df[
    genres_df["genre"].isin(top_genres)
]

genre_order = (
    genre_plot.groupby("genre")["positive_pct"]
    .median()
    .sort_values(ascending=False)
    .index
)

plt.figure(figsize=(11, 7))

sns.boxplot(
    data=genre_plot,
    x="positive_pct",
    y="genre",
    order=genre_order
)

plt.title("Steam Game Ratings by Genre")
plt.xlabel("Positive Reviews (%)")
plt.ylabel("Genre")

plt.tight_layout()
plt.savefig(
    FIGURES / "ratings_by_genre.png", dpi=300
)
plt.show()

# ---------------------------------
# 15. Figure 3: Most common tags
# ---------------------------------

top_tags = (
    tags_df["tag"]
    .value_counts()
    .head(15)
    .sort_values()
)

plt.figure(figsize=(11, 8))

sns.barplot(
    x=top_tags.values,
    y=top_tags.index,
    color="steelblue"
)

plt.title("15 Most Common Steam Community Tags")
plt.xlabel("Number of Games")
plt.ylabel("Community Tag")

plt.tight_layout()
plt.savefig(
    FIGURES / "most_common_tags.png", dpi=300
)
plt.show()


# ---------------------------------
# 16. Ratings by price category
# ---------------------------------

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

# Plot rating distributions by price category
plt.figure(figsize=(11, 7))

sns.boxplot(
    data=df,
    x="price_category",
    y="positive_pct",
    order=price_labels
)

plt.title("Steam Game Ratings by Price Category")
plt.xlabel("Original Game Price")
plt.ylabel("Positive Reviews (%)")

plt.xticks(rotation=20)
plt.tight_layout()

plt.savefig(
    FIGURES / "ratings_by_price_category.png",
    dpi=300
)

plt.show()


# ---------------------------------
# 17. Correlation analysis
# ---------------------------------

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


# ---------------------------------
# 18. Price and ratings by genre
# ---------------------------------

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

# Create a heatmap of median ratings

# Require at least 30 games per genre-price combination
MIN_GAMES = 30

filtered_summary = genre_price_summary.copy()

filtered_summary.loc[
    filtered_summary["games"] < MIN_GAMES,
    "median_rating"
] = float("nan")

heatmap_data = filtered_summary.pivot(
    index="genre",
    columns="price_category",
    values="median_rating"
)

# Preserve original price category ordering
heatmap_data = heatmap_data.reindex(
    columns=price_labels
)

# Remove genres with no qualifying cells
heatmap_data = heatmap_data.dropna(how="all")

# Display missing cells as blank
plt.figure(figsize=(12, 7))

sns.heatmap(
    heatmap_data,
    annot=True,
    fmt=".1f",
    cmap="YlGnBu",
    vmin=50,
    vmax=100,
    mask=heatmap_data.isna(),
    cbar_kws={
        "label": "Median Positive Reviews (%)"
    }
)

plt.title(
    "Steam Ratings by Genre and Price Category\n"
    "(Minimum 30 Games per Group)"
)

plt.xlabel("Original Game Price")
plt.ylabel("Genre")

plt.tight_layout()

plt.savefig(
    FIGURES / "genre_price_heatmap.png",
    dpi=300
)

plt.show()

# Preserve the price category order
heatmap_data = heatmap_data.reindex(
    columns=price_labels
)

plt.figure(figsize=(12, 7))

sns.heatmap(
    heatmap_data,
    annot=True,
    fmt=".1f",
    cmap="YlGnBu",
    vmin=50,
    vmax=100,
    cbar_kws={"label": "Median Positive Reviews (%)"}
)

plt.title("Steam Ratings by Genre and Price Category")
plt.xlabel("Original Game Price")
plt.ylabel("Genre")

plt.tight_layout()

plt.savefig(
    FIGURES / "genre_price_heatmap.png",
    dpi=300
)

plt.show()


# ---------------------------------
# 19. Community tag analysis
# ---------------------------------

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


# ---------------------------------
# 20. Normalized publisher analysis
# ---------------------------------

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


# ---------------------------------
# 21. Sensitivity analysis
# ---------------------------------

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


# ---------------------------------
# 22. Export analysis results
# ---------------------------------

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


# ---------------------------------
# 23. Release-year analysis
# ---------------------------------

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

# Release year vs. median rating
if not year_plot.empty:
    plt.figure(figsize=(12, 6))

    sns.lineplot(
        data=year_plot,
        x="release_year",
        y="median_rating",
        marker="o"
    )

    plt.title("Steam Game Ratings by Release Year")
    plt.xlabel("Release Year")
    plt.ylabel("Median Positive Reviews (%)")

    plt.tight_layout()
    plt.savefig(
        FIGURES / "ratings_by_release_year.png",
        dpi=300
    )
    plt.show()

# Export the summary
year_summary.to_csv(
    ANALYSIS_DIR / "release_year_summary.csv",
    index=False
)
