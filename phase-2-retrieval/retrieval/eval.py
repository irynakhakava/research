"""Пункт 5: offline eval retrieval на gold-set (Recall@k, MRR)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .embedders import Embedder
from .index import HybridIndex
from .retrieve import SearchHit, search


def load_gold_set(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def select_eval_cases(
    items: Sequence[dict[str, Any]],
    *,
    priorities: Sequence[str] | None = ("p0",),
    behaviors: Sequence[str] | None = ("answer",),
) -> list[dict[str, Any]]:
    """Оставляем кейсы для retrieval-метрик (по умолчанию answer + p0)."""
    pri = set(priorities) if priorities is not None else None
    beh = set(behaviors) if behaviors is not None else None
    out: list[dict[str, Any]] = []
    for item in items:
        if beh is not None and item.get("expected_behavior") not in beh:
            continue
        if pri is not None and item.get("source_priority") not in pri:
            continue
        if item.get("expected_behavior") == "answer" and not item.get("relevant_doc_ids"):
            continue
        out.append(item)
    return out


def ranked_doc_ids(hits: Sequence[SearchHit]) -> list[str]:
    """Уникальные doc_id в порядке первого появления в выдаче чанков."""
    seen: set[str] = set()
    ordered: list[str] = []
    for hit in hits:
        if hit.doc_id and hit.doc_id not in seen:
            seen.add(hit.doc_id)
            ordered.append(hit.doc_id)
    return ordered


def first_relevant_rank(
    retrieved_docs: Sequence[str],
    relevant_doc_ids: Sequence[str],
) -> int | None:
    """1-based rank первого релевантного документа; None если нет hit."""
    relevant = set(relevant_doc_ids)
    for i, doc_id in enumerate(retrieved_docs, start=1):
        if doc_id in relevant:
            return i
    return None


def recall_at_k(rank: int | None, k: int) -> float:
    if rank is None:
        return 0.0
    return 1.0 if rank <= k else 0.0


def reciprocal_rank(rank: int | None, *, k: int | None = None) -> float:
    """MRR contribution: 1/rank, optionally capped by k (RR@k)."""
    if rank is None:
        return 0.0
    if k is not None and rank > k:
        return 0.0
    return 1.0 / float(rank)


@dataclass
class CaseResult:
    id: str
    question: str
    relevant_doc_ids: list[str]
    primary_doc_id: str | None
    retrieved_doc_ids: list[str]
    retrieved_chunk_ids: list[str]
    first_relevant_rank: int | None
    hit_at: dict[int, bool] = field(default_factory=dict)
    rr: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "relevant_doc_ids": self.relevant_doc_ids,
            "primary_doc_id": self.primary_doc_id,
            "retrieved_doc_ids": self.retrieved_doc_ids,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "first_relevant_rank": self.first_relevant_rank,
            "hit_at": {str(k): v for k, v in self.hit_at.items()},
            "rr": self.rr,
        }


@dataclass
class EvalReport:
    mode: str
    k_values: list[int]
    n_cases: int
    metrics: dict[str, float]
    cases: list[CaseResult]
    thresholds: dict[str, float]
    passed: dict[str, bool]
    embedding_model: str | None = None
    priorities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "embedding_model": self.embedding_model,
            "priorities": self.priorities,
            "k_values": self.k_values,
            "n_cases": self.n_cases,
            "metrics": self.metrics,
            "thresholds": self.thresholds,
            "passed": self.passed,
            "cases": [c.to_dict() for c in self.cases],
        }


def evaluate_hits(
    cases: Sequence[dict[str, Any]],
    hits_by_id: dict[str, list[SearchHit]],
    *,
    k_values: Sequence[int] = (1, 5, 10),
    mrr_k: int = 10,
    mode: str = "hybrid",
    thresholds: dict[str, float] | None = None,
    embedding_model: str | None = None,
    priorities: Sequence[str] | None = None,
) -> EvalReport:
    """Считает метрики по уже полученным hit'ам (удобно для тестов)."""
    ks = sorted({int(k) for k in k_values if int(k) > 0})
    if not ks:
        raise ValueError("k_values must be non-empty positive ints")
    max_k = max(ks)
    thr = {
        "recall_at_10": 0.70,
        "mrr": 0.50,
        **(thresholds or {}),
    }

    results: list[CaseResult] = []
    recall_sums = {k: 0.0 for k in ks}
    mrr_sum = 0.0

    for item in cases:
        cid = str(item["id"])
        relevant = list(item.get("relevant_doc_ids") or [])
        hits = hits_by_id.get(cid, [])
        docs = ranked_doc_ids(hits)[:max_k]
        rank = first_relevant_rank(docs, relevant)
        hit_map = {k: recall_at_k(rank, k) >= 1.0 for k in ks}
        rr = reciprocal_rank(rank, k=mrr_k)
        for k in ks:
            recall_sums[k] += 1.0 if hit_map[k] else 0.0
        mrr_sum += rr
        results.append(
            CaseResult(
                id=cid,
                question=str(item.get("question", "")),
                relevant_doc_ids=relevant,
                primary_doc_id=item.get("primary_doc_id"),
                retrieved_doc_ids=docs,
                retrieved_chunk_ids=[h.chunk_id for h in hits[:max_k]],
                first_relevant_rank=rank,
                hit_at=hit_map,
                rr=rr,
            )
        )

    n = len(results)
    metrics: dict[str, float] = {}
    for k in ks:
        metrics[f"recall_at_{k}"] = (recall_sums[k] / n) if n else 0.0
    metrics["mrr"] = (mrr_sum / n) if n else 0.0
    metrics[f"mrr_at_{mrr_k}"] = metrics["mrr"]

    passed = {
        "recall_at_10": metrics.get("recall_at_10", 0.0) >= float(thr["recall_at_10"]),
        "mrr": metrics["mrr"] >= float(thr["mrr"]),
    }

    return EvalReport(
        mode=mode,
        k_values=ks,
        n_cases=n,
        metrics=metrics,
        cases=results,
        thresholds={k: float(v) for k, v in thr.items()},
        passed=passed,
        embedding_model=embedding_model,
        priorities=list(priorities or []),
    )


def run_eval(
    index: HybridIndex,
    embedder: Embedder,
    gold_items: Sequence[dict[str, Any]],
    *,
    mode: str = "hybrid",
    top_k: int = 10,
    candidate_k: int = 40,
    rrf_k: int = 60,
    k_values: Sequence[int] = (1, 5, 10),
    mrr_k: int = 10,
    priorities: Sequence[str] | None = ("p0",),
    thresholds: dict[str, float] | None = None,
) -> EvalReport:
    cases = select_eval_cases(gold_items, priorities=priorities, behaviors=("answer",))
    hits_by_id: dict[str, list[SearchHit]] = {}
    fetch_k = max(int(top_k), max(k_values) if k_values else 10)
    for item in cases:
        hits_by_id[str(item["id"])] = search(
            index,
            str(item["question"]),
            embedder,
            mode=mode,
            top_k=fetch_k,
            candidate_k=max(candidate_k, fetch_k),
            rrf_k=rrf_k,
        )
    return evaluate_hits(
        cases,
        hits_by_id,
        k_values=k_values,
        mrr_k=mrr_k,
        mode=mode,
        thresholds=thresholds,
        embedding_model=index.meta.get("embedding_model"),
        priorities=priorities,
    )


def write_report(report: EvalReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
