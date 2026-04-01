from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any
import os, json
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv

from .docs import DocAlignmentModel
from .schema import NodeSchema


load_dotenv()
print("SKIP_FIELDS =", os.getenv("SKIP_FIELDS"))  # debug

MISSING_STRINGS = {"", "na", "n/a", "none", "null", "nan", "not reported"}
IDENTIFIER_HINTS = ("_id", "_record_id", "uuid", "crdc_id")


@dataclass(frozen=True)
class PairwiseFeatures:
    support: float
    predictive_strength: float
    determinism: float
    stability: float
    doc_alignment: float
    heldout_accuracy: float
    baseline_accuracy: float
    row_count: int
    total_rows: int
    train_rows: int
    test_rows: int

def build_conditional_map(df: pd.DataFrame, A: str, B: str, deterministic_threshold=0.95):
    mapping = {}

    grouped = df.groupby(A)

    for a_val, subset in grouped:
        counts = subset[B].value_counts(normalize=True)

        top_val = counts.index[0]
        top_prob = counts.iloc[0]

        if top_prob >= deterministic_threshold:
            mapping[str(a_val)] = str(top_val)
        else:
            mapping[str(a_val)] = [str(v) for v in counts.index]

    return mapping
def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in MISSING_STRINGS:
        return True
    return False


def normalize_value(value: Any) -> str:
    if is_missing(value):
        return ""
    return str(value).strip()


def is_identifier_like(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.endswith(hint) or lowered == hint.strip("_") for hint in IDENTIFIER_HINTS)


def prepare_pair_frame(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    pair = df[[a, b]].copy()
    pair[a] = pair[a].map(normalize_value)
    pair[b] = pair[b].map(normalize_value)
    pair = pair[(pair[a] != "") & (pair[b] != "")]
    return pair.reset_index(drop=True)


def conditional_determinism(pair: pd.DataFrame, a: str, b: str) -> float:
    if pair.empty:
        return 0.0

    weighted_max_probs = []
    total = len(pair)
    for a_val, group in pair.groupby(a):
        counts = group[b].value_counts(normalize=True)
        if counts.empty:
            continue
        weight = len(group) / total
        weighted_max_probs.append(weight * float(counts.max()))
    return float(np.clip(sum(weighted_max_probs), 0.0, 1.0))


def predictive_strength_from_holdout(pair: pd.DataFrame, a: str, b: str, *, seed: int = 42) -> tuple[float, float, float, int, int]:
    if pair.empty or pair[a].nunique() < 2 or pair[b].nunique() < 2:
        return 0.0, 0.0, 0.0, 0, 0

    X = pair[[a]].astype(str)
    y = pair[b].astype(str)

    # If the target is extremely small, use the full data as a fall-back signal.
    if len(pair) < 8:
        baseline = float(y.value_counts(normalize=True).max())
        return baseline, baseline, 0.0, len(pair), 0

    stratify = y if y.value_counts().min() >= 2 else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=seed,
            stratify=stratify,
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=seed,
            shuffle=True,
        )

    if y_train.nunique() < 2 or y_test.empty:
        baseline = float(y_test.value_counts(normalize=True).max()) if len(y_test) else float(y.value_counts(normalize=True).max())
        return baseline, baseline, 0.0, len(X_train), len(X_test)

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), [a]),
        ],
        remainder="drop",
    )
    model = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("clf", LogisticRegression(max_iter=2000)),
        ]
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, pred))

    majority = y_train.value_counts().idxmax()
    baseline_pred = np.full(len(y_test), majority)
    baseline = float(accuracy_score(y_test, baseline_pred))

    if baseline >= 1.0:
        predictive_strength = 0.0
    else:
        predictive_strength = max(0.0, (accuracy - baseline) / max(1e-9, 1.0 - baseline))

    return predictive_strength, accuracy, baseline, len(X_train), len(X_test)


def stability_from_resamples(pair: pd.DataFrame, a: str, b: str, *, n_splits: int = 5) -> float:
    if pair.empty or len(pair) < 8:
        return 0.0

    scores: list[float] = []
    for seed in range(n_splits):
        score, _, _, _, _ = predictive_strength_from_holdout(pair, a, b, seed=seed)
        scores.append(score)

    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores))
    if mean_score <= 1e-9:
        return 0.0
    return float(np.clip(mean_score / (mean_score + std_score + 1e-9), 0.0, 1.0))


@dataclass
class PairwiseFeatureEngine:
    node_schema: NodeSchema
    doc_model: DocAlignmentModel
    weights: dict[str, float] | None = None

    def __post_init__(self) -> None:
        self.weights = self.weights or {
            "support": 0.25,
            "predictive_strength": 0.30,
            "determinism": 0.20,
            "stability": 0.15,
            "doc_alignment": 0.10,
        }

    def should_skip(self, name: str) -> bool:
        if is_identifier_like(name):
            return True
        if name in self.node_schema.exclude_like:
            return True
        return False

    def evaluate_pair(self, df: pd.DataFrame, a: str, b: str) -> dict[str, Any]:
        pair = prepare_pair_frame(df, a, b)
        total_rows = len(df)
        row_count = len(pair)
        support = float(row_count / total_rows) if total_rows else 0.0

        predictive_strength, heldout_accuracy, baseline_accuracy, train_rows, test_rows = predictive_strength_from_holdout(pair, a, b)
        determinism = conditional_determinism(pair, a, b)
        stability = stability_from_resamples(pair, a, b)
        doc_alignment = float(self.doc_model.score(a, b))

        strength = (
            self.weights["support"] * support
            + self.weights["predictive_strength"] * predictive_strength
            + self.weights["determinism"] * determinism
            + self.weights["stability"] * stability
            + self.weights["doc_alignment"] * doc_alignment
        )

        evidence = self._build_evidence(pair, a, b)
        classification = self.classify_strength(strength)
        a_to_b_map = build_conditional_map(pair, a, b)

        return {
            "A": a,
            "B": b,
            "support": support,
            "predictive_strength": predictive_strength,
            "determinism": determinism,
            "stability": stability,
            "doc_alignment": doc_alignment,
            "strength": float(np.clip(strength, 0.0, 1.0)),
            "classification": classification,
            "heldout_accuracy": heldout_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "row_count": row_count,
            "total_rows": total_rows,
            "train_rows": train_rows,
            "test_rows": test_rows,
            "evidence": evidence,
            "a_to_b_mapping": json.dumps(a_to_b_map)
        }

    def _build_evidence(self, pair: pd.DataFrame, a: str, b: str, limit: int = 5) -> list[dict[str, Any]]:
        if pair.empty:
            return []

        evidence: list[dict[str, Any]] = []
        for a_val, group in pair.groupby(a):
            counts = group[b].value_counts(normalize=True)
            if counts.empty:
                continue
            evidence.append(
                {
                    "A_value": a_val,
                    "count": int(len(group)),
                    "top_B_values": [
                        {"value": idx, "probability": float(prob)}
                        for idx, prob in counts.head(3).items()
                    ],
                }
            )
        evidence.sort(key=lambda item: item["count"], reverse=True)
        return evidence[:limit]

    @staticmethod
    def classify_strength(score: float) -> str:
        if score >= 0.9:
            return "functional"
        if score >= 0.7:
            return "strong" 
        if score >= 0.45:
            return "conditional"
        if score >= 0.2:
            return "weak"
        return "independent"
    

    def get_skip_fields(self) -> set[str]:
        raw = os.getenv("SKIP_FIELDS", "")
        return {x.strip().lower() for x in raw.split(",") if x.strip()}

    def should_skip(self, col: str, schema: NodeSchema | None = None) -> bool:
        col_norm = col.strip().lower()

        # env-based skip
        if col_norm in self.get_skip_fields():
            return True

        # identifier-like skip
        if is_identifier_like(col_norm):
            return True

        # schema-based skip
        if schema is not None:
            if col in schema.exclude_like:
                return True
            if col not in schema.properties:
                return True

        return False

        # if col in skip_names:
        #     return True

        # if schema is not None:
        #     if col in schema.exclude_like:
        #         return True

        #     prop = schema.properties.get(col)
        #     if prop is None:
        #         return True

        # return False

    def get_model_columns(self, schema: NodeSchema, df: pd.DataFrame) -> list[str]:
        schema_columns = list(schema.properties.keys())
        return [c for c in schema_columns if c in df.columns and not self.should_skip(c, schema)]

    def evaluate_all_pairs(self, schema: NodeSchema, df: pd.DataFrame) -> pd.DataFrame:
        # columns = [c for c in df.columns if not self.should_skip(c)]
        results: list[dict[str, Any]] = []
        columns = self.get_model_columns(schema, df)
        for a in columns:
            for b in columns:
                if a == b:
                    continue
                result = self.evaluate_pair(df, a, b)
                results.append(result)

        results_df = pd.DataFrame(results)
        if not results_df.empty:
            results_df = results_df.sort_values(["strength", "predictive_strength", "support"], ascending=False).reset_index(drop=True)
        return results_df
