"""Офлайн-проверка /ask на gold-set: refuse-rate и контракт citations[]."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from retrieval.embedders import Embedder
from retrieval.index import HybridIndex

from .ask import AskResponse, ask


def load_gold_set(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def citation_ok(resp: AskResponse) -> bool:
    """DoD #5: citations[] с path (url желателен)."""
    if resp.refuse and not resp.citations:
        # empty retrieval — цитат может не быть
        return resp.refuse_reason in {"empty_retrieval", "empty_query"}
    if not resp.citations:
        return False
    return all(bool(c.path) for c in resp.citations)


def grounded_ok(resp: AskResponse, relevant_doc_ids: Sequence[str]) -> bool:
    """Хотя бы одна цитата указывает на эталонный документ."""
    if resp.refuse:
        return True
    relevant = set(relevant_doc_ids)
    if not relevant:
        return True
    return any(c.doc_id in relevant for c in resp.citations)


@dataclass
class AskEvalReport:
    n_refuse_cases: int
    n_answer_cases: int
    refuse_rate: float
    citation_contract_rate: float
    grounded_rate: float
    thresholds: dict[str, float]
    passed: dict[str, bool]
    cases: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_refuse_cases": self.n_refuse_cases,
            "n_answer_cases": self.n_answer_cases,
            "refuse_rate": self.refuse_rate,
            "citation_contract_rate": self.citation_contract_rate,
            "grounded_rate": self.grounded_rate,
            "thresholds": self.thresholds,
            "passed": self.passed,
            "cases": self.cases,
        }


def run_ask_eval(
    index: HybridIndex,
    embedder: Embedder,
    gold_items: Sequence[dict[str, Any]],
    *,
    ask_kwargs: dict[str, Any],
    priorities: Sequence[str] = ("p0",),
    answer_limit: int | None = None,
    threshold_refuse: float = 0.90,
    threshold_citations: float = 1.0,
    threshold_grounded: float = 0.80,
) -> AskEvalReport:
    pri = set(priorities)
    refuse_items = [
        i
        for i in gold_items
        if i.get("expected_behavior") == "refuse" and i.get("source_priority") in pri
    ]
    answer_items = [
        i
        for i in gold_items
        if i.get("expected_behavior") == "answer"
        and i.get("source_priority") in pri
        and i.get("relevant_doc_ids")
    ]
    if answer_limit is not None:
        answer_items = answer_items[:answer_limit]

    cases: list[dict[str, Any]] = []
    refuse_ok = 0
    cite_ok = 0
    ground_ok = 0
    total = 0

    for item in refuse_items + answer_items:
        resp = ask(index, embedder, str(item["question"]), **ask_kwargs)
        expected = str(item.get("expected_behavior"))
        is_refuse_ok = expected != "refuse" or resp.refuse
        is_cite = citation_ok(resp)
        is_ground = grounded_ok(resp, item.get("relevant_doc_ids") or [])
        if expected == "refuse" and resp.refuse:
            refuse_ok += 1
        if is_cite:
            cite_ok += 1
        if expected == "answer" and is_ground:
            ground_ok += 1
        total += 1
        cases.append(
            {
                "id": item.get("id"),
                "expected_behavior": expected,
                "refuse": resp.refuse,
                "refuse_reason": resp.refuse_reason,
                "citation_ok": is_cite,
                "grounded_ok": is_ground,
                "refuse_ok": is_refuse_ok,
                "citation_doc_ids": [c.doc_id for c in resp.citations],
            }
        )

    n_ref = len(refuse_items)
    n_ans = len(answer_items)
    refuse_rate = (refuse_ok / n_ref) if n_ref else 1.0
    cite_rate = (cite_ok / total) if total else 0.0
    grounded_rate = (ground_ok / n_ans) if n_ans else 1.0
    thresholds = {
        "refuse_rate": threshold_refuse,
        "citation_contract_rate": threshold_citations,
        "grounded_rate": threshold_grounded,
    }
    passed = {
        "refuse_rate": refuse_rate >= threshold_refuse,
        "citation_contract_rate": cite_rate >= threshold_citations,
        "grounded_rate": grounded_rate >= threshold_grounded,
    }
    return AskEvalReport(
        n_refuse_cases=n_ref,
        n_answer_cases=n_ans,
        refuse_rate=refuse_rate,
        citation_contract_rate=cite_rate,
        grounded_rate=grounded_rate,
        thresholds=thresholds,
        passed=passed,
        cases=cases,
    )
