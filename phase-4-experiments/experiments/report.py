"""Текстовый отчёт по сетке экспериментов."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 · experiment report",
        "",
        f"Index: `{report.get('index_dir', '')}`",
        f"Gold-set: `{report.get('gold_set', '')}`",
        "",
    ]
    retrieval = [r for r in report.get("runs", []) if r.get("kind") == "retrieval"]
    ask_rows = [r for r in report.get("runs", []) if r.get("kind") == "ask"]
    if retrieval:
        lines += [
            "## Retrieval (answer / p0)",
            "",
            "| mode | Recall@1 | Recall@5 | Recall@10 | MRR | n |",
            "|------|----------|----------|-----------|-----|---|",
        ]
        for row in retrieval:
            m = row["metrics"]
            mode = row["params"].get("mode", "")
            lines.append(
                "| {mode} | {r1} | {r5} | {r10} | {mrr} | {n} |".format(
                    mode=mode,
                    r1=_fmt(m.get("recall_at_1")),
                    r5=_fmt(m.get("recall_at_5")),
                    r10=_fmt(m.get("recall_at_10")),
                    mrr=_fmt(m.get("mrr")),
                    n=row.get("n_cases"),
                )
            )
        lines.append("")
    if ask_rows:
        lines += [
            "## /ask",
            "",
            "| backend | min_dense | top_k | refuse | answered | grounded (answered) | citations |",
            "|---------|-----------|-------|--------|----------|---------------------|-----------|",
        ]
        for row in ask_rows:
            m = row["metrics"]
            p = row["params"]
            lines.append(
                "| {b} | {s} | {k} | {rf} | {ar} | {ga} | {cc} |".format(
                    b=p.get("generation_backend"),
                    s=_fmt(p.get("min_dense_score")),
                    k=p.get("top_k"),
                    rf=_fmt(m.get("refuse_rate")),
                    ar=_fmt(m.get("answered_rate")),
                    ga=_fmt(m.get("grounded_among_answered")),
                    cc=_fmt(m.get("citation_contract_rate")),
                )
            )
        lines.append("")
    winners = report.get("winners") or {}
    if winners:
        lines += ["## Winners", ""]
        if "retrieval" in winners:
            w = winners["retrieval"]
            lines.append(
                f"- retrieval: **{w['params'].get('mode')}** "
                f"(Recall@10={_fmt(w.get('recall_at_10'))}, MRR={_fmt(w.get('mrr'))})"
            )
        if "ask" in winners:
            w = winners["ask"]
            p = w.get("params") or {}
            lines.append(
                f"- /ask: **{p.get('generation_backend')}** "
                f"min_dense_score={p.get('min_dense_score')} top_k={p.get('top_k')}"
            )
        lines.append("")
        lines.append(
            "На маленьком p0-корпусе dense часто чуть лучше hybrid по MRR — "
            "это не повод выкидывать BM25 на большем наборе."
        )
        lines.append("")
    return "\n".join(lines)
