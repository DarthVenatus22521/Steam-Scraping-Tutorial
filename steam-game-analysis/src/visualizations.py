"""Matplotlib/seaborn plotting functions; never call data-collection APIs."""

import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns


def plot_price_scatter(df, figures_dir: Path):
    """Scatterplot of listed original price and positive review percentage."""
    FIGURES = Path(figures_dir)
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
    plt.close()


def plot_genre_ratings(genres_df, figures_dir: Path):
    """Boxplot showing distribution of positive ratings across common genres."""
    FIGURES = Path(figures_dir)
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
    plt.close()


def plot_tag_counts(tags_df, figures_dir: Path):
    """Bar chart of the most frequent retrieved community tags."""
    FIGURES = Path(figures_dir)
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
    plt.close()


def plot_price_categories(df, price_labels, figures_dir: Path):
    """Boxplot of positive ratings for original-price categories."""
    FIGURES = Path(figures_dir)
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

    plt.close()


def plot_genre_price_heatmap(genre_price_summary, price_labels, figures_dir: Path):
    """Show medians only where genre-price groups have at least 30 games."""
    FIGURES = Path(figures_dir)
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

    plt.close()


def plot_release_year(year_plot, figures_dir: Path):
    """Plot rating by release year for years with at least 20 sampled games."""
    FIGURES = Path(figures_dir)
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
        plt.close()


