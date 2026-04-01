from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


def _safe_filename(value: str) -> str:
    cleaned = []
    for ch in value.lower().strip():
        if ch.isalnum() or ch in {"-", "_"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    out = "".join(cleaned).strip("_")
    return out or "chart"


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def _save_bar_chart(series: pd.Series, title: str, xlabel: str, ylabel: str, out_path: Path) -> Path:
    plt.figure(figsize=(10, 6))
    series.plot(kind="bar")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()
    return out_path


def _save_histogram(values: pd.Series, title: str, xlabel: str, ylabel: str, out_path: Path) -> Path:
    plt.figure(figsize=(10, 6))
    plt.hist(values.dropna(), bins=20)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()
    return out_path


def _save_scatter(x: pd.Series, y: pd.Series, title: str, xlabel: str, ylabel: str, out_path: Path) -> Path:
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, alpha=0.7)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()
    return out_path


def generate_visual_report(
    results: pd.DataFrame,
    output_dir: str | Path,
    top_n: int = 15,
) -> list[Path]:
    """
    Generate lightweight PNG visualizations for a pairwise relationship table.

    Returns a list of saved chart paths.
    The function is intentionally defensive so it works across slightly different
    result schemas.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_paths: list[Path] = []

    if results is None or results.empty:
        empty_path = output_dir / "no_results.png"
        plt.figure(figsize=(8, 4))
        plt.text(0.5, 0.5, "No relationships found", ha="center", va="center", fontsize=14)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(empty_path, dpi=160, bbox_inches="tight")
        plt.close()
        return [empty_path]

    df = results.copy()

    # 1) Relationship/classification counts
    classification_col = _first_existing_column(
        df,
        ["classification", "relationship_type", "label", "category", "class"],
    )
    if classification_col and df[classification_col].notna().any():
        counts = (
            df[classification_col]
            .fillna("unknown")
            .astype(str)
            .value_counts()
            .head(top_n)
        )
        out_path = output_dir / f"{_safe_filename(classification_col)}_counts.png"
        chart_paths.append(
            _save_bar_chart(
                counts,
                title="Relationship counts",
                xlabel=classification_col,
                ylabel="Count",
                out_path=out_path,
            )
        )

    # 2) Top relationships by score/confidence if present
    score_col = _first_existing_column(
        df,
        ["score", "confidence", "probability", "similarity", "weight"],
    )
    if score_col and pd.api.types.is_numeric_dtype(df[score_col]):
        top_scores = (
            df[[score_col]]
            .dropna()
            .sort_values(score_col, ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
        top_scores.index = [f"#{i+1}" for i in range(len(top_scores))]
        out_path = output_dir / f"{_safe_filename(score_col)}_top.png"
        chart_paths.append(
            _save_bar_chart(
                top_scores[score_col],
                title=f"Top {min(top_n, len(top_scores))} rows by {score_col}",
                xlabel="Row",
                ylabel=score_col,
                out_path=out_path,
            )
        )

        hist_path = output_dir / f"{_safe_filename(score_col)}_histogram.png"
        chart_paths.append(
            _save_histogram(
                df[score_col],
                title=f"Distribution of {score_col}",
                xlabel=score_col,
                ylabel="Frequency",
                out_path=hist_path,
            )
        )

    # 3) Relationship pair counts, if we can infer source/target columns
    source_col = _first_existing_column(
        df,
        ["source", "source_property", "left", "left_property", "property_a", "prop_a", "from"],
    )
    target_col = _first_existing_column(
        df,
        ["target", "target_property", "right", "right_property", "property_b", "prop_b", "to"],
    )
    if source_col and target_col:
        pair_series = (
            df[[source_col, target_col]]
            .fillna("")
            .astype(str)
            .agg(" -> ".join, axis=1)
            .value_counts()
            .head(top_n)
        )
        out_path = output_dir / "top_pairs.png"
        chart_paths.append(
            _save_bar_chart(
                pair_series,
                title=f"Top {min(top_n, len(pair_series))} pairs",
                xlabel="Pair",
                ylabel="Count",
                out_path=out_path,
            )
        )

    # 4) If we have two numeric columns, create a simple scatter for the first pair
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[:2]
        scatter_path = output_dir / f"{_safe_filename(x_col)}_vs_{_safe_filename(y_col)}.png"
        chart_paths.append(
            _save_scatter(
                df[x_col],
                df[y_col],
                title=f"{x_col} vs {y_col}",
                xlabel=x_col,
                ylabel=y_col,
                out_path=scatter_path,
            )
        )

    return chart_paths


__all__ = ["generate_visual_report"]