"""Сетки сравнений: режимы retrieval и параметры /ask."""

from __future__ import annotations

from typing import Any, Sequence

from generation.ask import ask
from generation.eval import run_ask_eval
from retrieval.embedders import Embedder
from retrieval.eval import run_eval
from retrieval.index import HybridIndex


def summarize_ask_cases(cases: Sequence[dict[str, Any]]) -> dict[str, float]:
    """Доп. метрики: отказ на answer-кейсах не должен считаться «grounded»."""
    answers = [c for c in cases if c.get("expected_behavior") == "answer"]
    refuses = [c for c in cases if c.get("expected_behavior") == "refuse"]
    answered = [c for c in answers if not c.get("refuse")]
    n_ans = len(answers)
    n_ref = len(refuses)
    grounded_answered = [
        c for c in answered if c.get("grounded_ok")
    ]
    return {
        "answer_refuse_rate": (1.0 - len(answered) / n_ans) if n_ans else 0.0,
        "answered_rate": (len(answered) / n_ans) if n_ans else 1.0,
        "grounded_among_answered": (
            len(grounded_answered) / len(answered) if answered else 0.0
        ),
        "refuse_rate": (
            sum(1 for c in refuses if c.get("refuse")) / n_ref if n_ref else 1.0
        ),
    }


def run_retrieval_sweep(
    index: HybridIndex,
    embedder: Embedder,
    gold_items: Sequence[dict[str, Any]],
    *,
    modes: Sequence[str],
    top_k: int = 10,
    candidate_k: int = 40,
    rrf_k: int = 60,
    k_values: Sequence[int] = (1, 5, 10),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode in modes:
        report = run_eval(
            index,
            embedder,
            gold_items,
            mode=mode,
            top_k=top_k,
            candidate_k=candidate_k,
            rrf_k=rrf_k,
            k_values=k_values,
            mrr_k=max(k_values) if k_values else 10,
            priorities=["p0"],
        )
        rows.append(
            {
                "name": f"retrieve:{mode}",
                "kind": "retrieval",
                "params": {"mode": mode, "top_k": top_k},
                "metrics": report.metrics,
                "passed": report.passed,
                "n_cases": report.n_cases,
            }
        )
    return rows


def run_ask_sweep(
    index: HybridIndex,
    embedder: Embedder,
    gold_items: Sequence[dict[str, Any]],
    *,
    base_ask_kwargs: dict[str, Any],
    min_dense_scores: Sequence[float] | None = None,
    top_ks: Sequence[int] | None = None,
    answer_limit: int | None = None,
    generation_backends: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scores = list(min_dense_scores or [float(base_ask_kwargs.get("min_dense_score", 0.28))])
    ks = list(top_ks or [int(base_ask_kwargs.get("top_k", 5))])
    backends = list(generation_backends or [str(base_ask_kwargs.get("generation_backend", "extractive"))])

    for backend in backends:
        for score in scores:
            for top_k in ks:
                kwargs = dict(base_ask_kwargs)
                kwargs["min_dense_score"] = float(score)
                kwargs["top_k"] = int(top_k)
                kwargs["generation_backend"] = backend
                if backend == "extractive":
                    kwargs["generation_model"] = "extractive"
                report = run_ask_eval(
                    index,
                    embedder,
                    gold_items,
                    ask_kwargs=kwargs,
                    answer_limit=answer_limit,
                )
                extra = summarize_ask_cases(report.cases)
                rows.append(
                    {
                        "name": f"ask:{backend}:score={score}:top_k={top_k}",
                        "kind": "ask",
                        "params": {
                            "generation_backend": backend,
                            "min_dense_score": float(score),
                            "top_k": int(top_k),
                        },
                        "metrics": {
                            "refuse_rate": report.refuse_rate,
                            "citation_contract_rate": report.citation_contract_rate,
                            "grounded_rate": report.grounded_rate,
                            **extra,
                        },
                        "passed": report.passed,
                        "n_refuse_cases": report.n_refuse_cases,
                        "n_answer_cases": report.n_answer_cases,
                    }
                )
    return rows


def pick_winners(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    retrieval = [r for r in rows if r.get("kind") == "retrieval"]
    ask_rows = [r for r in rows if r.get("kind") == "ask"]
    winners: dict[str, Any] = {}
    if retrieval:
        best = max(
            retrieval,
            key=lambda r: (
                float(r["metrics"].get("recall_at_10", 0.0)),
                float(r["metrics"].get("mrr", 0.0)),
            ),
        )
        winners["retrieval"] = {
            "name": best["name"],
            "params": best["params"],
            "recall_at_10": best["metrics"].get("recall_at_10"),
            "mrr": best["metrics"].get("mrr"),
        }
    if ask_rows:
        # сначала пороги DoD, потом меньше ложных refuse на answer, потом grounded
        def ask_key(r: dict[str, Any]) -> tuple:
            m = r["metrics"]
            dod = (
                1
                if (
                    float(m.get("refuse_rate", 0)) >= 0.90
                    and float(m.get("citation_contract_rate", 0)) >= 1.0
                    and float(m.get("grounded_among_answered", 0)) >= 0.80
                )
                else 0
            )
            return (
                dod,
                float(m.get("answered_rate", 0.0)),
                float(m.get("grounded_among_answered", 0.0)),
                float(m.get("refuse_rate", 0.0)),
            )

        best_ask = max(ask_rows, key=ask_key)
        winners["ask"] = {
            "name": best_ask["name"],
            "params": best_ask["params"],
            "metrics": best_ask["metrics"],
        }
    return winners


# re-export ask for type checkers / tests that patch
__all__ = [
    "ask",
    "pick_winners",
    "run_ask_sweep",
    "run_retrieval_sweep",
    "summarize_ask_cases",
]
