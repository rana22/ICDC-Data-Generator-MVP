from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_markdown_report(df: pd.DataFrame, path: str | Path, top_n: int = 15) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Strongest property relationships", ""]
    if df.empty:
        lines.append("No relationships were detected.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    for i, row in df.head(top_n).iterrows():
        lines.append(f"## {i + 1}. {row['A']} → {row['B']}")
        lines.append(f"- classification: **{row['classification']}**")
        lines.append(f"- strength: `{row['strength']:.3f}`")
        lines.append(f"- predictive strength: `{row['predictive_strength']:.3f}`")
        lines.append(f"- support: `{row['support']:.3f}`")
        lines.append(f"- determinism: `{row['determinism']:.3f}`")
        lines.append(f"- stability: `{row['stability']:.3f}`")
        lines.append(f"- doc alignment: `{row['doc_alignment']:.3f}`")
        lines.append(f"- heldout accuracy: `{row['heldout_accuracy']:.3f}`")
        lines.append(f"- baseline accuracy: `{row['baseline_accuracy']:.3f}`")
        lines.append("")
        evidence = row.get("evidence", []) or []
        if evidence:
            lines.append("Evidence:")
            for item in evidence[:3]:
                lines.append(f"- `{item['A_value']}` (n={item['count']}): " + ", ".join(f"{x['value']}={x['probability']:.2f}" for x in item["top_B_values"]))
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
