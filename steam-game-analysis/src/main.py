"""Offline entry point for the Steam game data-analysis project.

Run from project root: uv run python src/main.py
The API collectors are independent and are never invoked here.
"""

from pathlib import Path
import seaborn as sns

from data_processing import (
    load_and_prepare_data, save_cleaned_tables, validate_data, print_data_summary,
)
from eda import (
    analyze_prices, analyze_correlations, analyze_genre_prices, analyze_tags,
    analyze_publishers, analyze_sensitivity, analyze_release_year,
    export_analysis_results,
)
from visualizations import (
    plot_price_scatter, plot_genre_ratings, plot_tag_counts,
    plot_price_categories, plot_genre_price_heatmap, plot_release_year,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
PRICE_LABELS = [
    "Free", "$0.01–$5", "$5.01–$10", "$10.01–$20",
    "$20.01–$40", "Over $40",
]


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    games, genres, tags, publishers = load_and_prepare_data(DATA)
    save_cleaned_tables(games, genres, tags, DATA)
    validate_data(games, genres, tags, publishers)
    print_data_summary(games, genres, tags)

    plot_price_scatter(games, FIGURES)
    plot_genre_ratings(genres, FIGURES)
    plot_tag_counts(tags, FIGURES)

    price_summary = analyze_prices(games)
    plot_price_categories(games, PRICE_LABELS, FIGURES)
    analyze_correlations(games)

    genre_price_summary = analyze_genre_prices(games, genres)
    plot_genre_price_heatmap(genre_price_summary, PRICE_LABELS, FIGURES)

    tag_summary = analyze_tags(games, tags)
    publisher_summary = analyze_publishers(publishers)
    sensitivity_summary, sensitivity_price_summary = analyze_sensitivity(games)

    year_summary, year_plot = analyze_release_year(games)
    plot_release_year(year_plot, FIGURES)

    export_analysis_results(
        DATA, FIGURES, price_summary, genre_price_summary, tag_summary,
        publisher_summary, sensitivity_summary, sensitivity_price_summary,
        year_summary,
    )


if __name__ == "__main__":
    main()
