"""Matplotlib/seaborn plotting functions; never call data-collection APIs."""

import matplotlib
matplotlib.use("Agg")

from matplotlib.ticker import MultipleLocator, FormatStrFormatter

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
        color="#4361EE",
        edgecolor="#293B86",
        linewidth=0.6
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
    """Boxplot with a distinct color for each price category."""
    FIGURES = Path(figures_dir)

    price_palette = {
        "Free": "#6C757D",
        "$0.01–$5": "#2A9D8F",
        "$5.01–$10": "#4CC9F0",
        "$10.01–$20": "#F4A261",
        "$20.01–$40": "#E76F51",
        "Over $40": "#9C6644"
    }

    plt.figure(figsize=(11, 7))

    sns.boxplot(
        data=df,
        x="price_category",
        y="positive_pct",
        hue="price_category",
        order=price_labels,
        hue_order=price_labels,
        palette=price_palette,
        dodge=False,
        legend=False,
        linewidth=1.2,
        flierprops={
            "marker": "o",
            "markersize": 4,
            "alpha": 0.4,
            "markeredgecolor": "#555555"
        }
    )

    plt.title(
        "Steam Game Ratings by Price Category",
        fontsize=16,
        fontweight="bold",
        pad=15
    )
    plt.xlabel("Original Game Price (USD)")
    plt.ylabel("Positive Reviews (%)")

    # Display dollar signs literally
    display_labels = [
        "Free",
        r"\$0.01–\$5",
        r"\$5.01–\$10",
        r"\$10.01–\$20",
        r"\$20.01–\$40",
        "Over \$40"
    ]

    ax = plt.gca()
    ax.set_xticklabels(display_labels, rotation=20, ha="right")
    plt.ylim(10, 101)
    plt.tight_layout()

    plt.savefig(
        FIGURES / "ratings_by_price_category.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()




def plot_genre_price_heatmap(
    genre_price_summary,
    price_labels,
    figures_dir: Path
):
    """Heatmap with a 30-game minimum and blue-neutral-red colors."""
    FIGURES = Path(figures_dir)
    MIN_GAMES = 30

    filtered_summary = genre_price_summary.copy()

    # Hide groups containing fewer than 30 games
    filtered_summary.loc[
        filtered_summary["games"] < MIN_GAMES,
        "median_rating"
    ] = float("nan")

    heatmap_data = filtered_summary.pivot(
        index="genre",
        columns="price_category",
        values="median_rating"
    )

    # Preserve the original category order
    heatmap_data = heatmap_data.reindex(
        columns=price_labels
    )

    # Remove genres with no qualifying groups
    heatmap_data = heatmap_data.dropna(how="all")

    plt.figure(figsize=(12, 7))

    ax = sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=".1f",
        cmap="RdBu_r",
        center=82.5,
        vmin=70,
        vmax=92,
        mask=heatmap_data.isna(),
        linewidths=1,
        linecolor="white",
        annot_kws={
            "fontsize": 10,
            "fontweight": "bold",
            "color": "black"
        },
        cbar_kws={
            "label": "Median Positive Reviews (%)"
        }
    )

    # Make blank cells visibly intentional
    ax.set_facecolor("#F2F2F2")

    ax.grid(False)

    plt.title(
        "Steam Ratings by Genre and Price Category\n"
        "(Blank Cells Indicate Fewer Than 30 Games)",
        fontsize=15,
        fontweight="bold",
        pad=15
    )

    plt.xlabel("Original Game Price")
    plt.ylabel("Genre")

    # Force labels to display clearly
    
   
    # Display dollar signs literally instead of as math formatting
    display_labels = [
        "Free",
        r"\$0.01–\$5",
        r"\$5.01–\$10",
        r"\$10.01–\$20",
        r"\$20.01–\$40",
        "Over $40"
    ]

    ax.set_xticklabels(display_labels, rotation=0)
    ax.tick_params(axis="y", labelrotation=0)

    plt.tight_layout()

    plt.savefig(
        FIGURES / "genre_price_heatmap.png",
        dpi=300,
        bbox_inches="tight"
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

        
        # Display whole-number years every 2 years
        ax = plt.gca()
        ax.xaxis.set_major_locator(MultipleLocator(2))
        ax.xaxis.set_major_formatter(FormatStrFormatter("%d"))


        plt.tight_layout()
        plt.savefig(
            FIGURES / "ratings_by_release_year.png",
            dpi=300
        )
        plt.close()


