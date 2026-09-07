"""Простой BM25 Okapi без внешних зависимостей."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_/+.-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class BM25Index:
    """Сериализуемый BM25 по списку документов (у нас — чанки)."""

    doc_ids: list[str]
    doc_len: list[int]
    avgdl: float
    # term -> list of (doc_index, tf)
    postings: dict[str, list[tuple[int, int]]]
    df: dict[str, int]
    n_docs: int
    k1: float = 1.5
    b: float = 0.75

    def score(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        q_terms = tokenize(query)
        if not q_terms or self.n_docs == 0:
            return []
        scores = [0.0] * self.n_docs
        for term in q_terms:
            df = self.df.get(term)
            if not df:
                continue
            idf = math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
            for doc_idx, tf in self.postings.get(term, []):
                dl = self.doc_len[doc_idx]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[doc_idx] += idf * (tf * (self.k1 + 1)) / denom
        ranked = sorted(
            ((self.doc_ids[i], scores[i]) for i in range(self.n_docs) if scores[i] > 0),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]

    def to_dict(self) -> dict:
        return {
            "doc_ids": self.doc_ids,
            "doc_len": self.doc_len,
            "avgdl": self.avgdl,
            "postings": {
                term: [[i, tf] for i, tf in pairs] for term, pairs in self.postings.items()
            },
            "df": self.df,
            "n_docs": self.n_docs,
            "k1": self.k1,
            "b": self.b,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BM25Index:
        postings = {
            term: [(int(i), int(tf)) for i, tf in pairs]
            for term, pairs in data["postings"].items()
        }
        return cls(
            doc_ids=list(data["doc_ids"]),
            doc_len=list(data["doc_len"]),
            avgdl=float(data["avgdl"]),
            postings=postings,
            df={k: int(v) for k, v in data["df"].items()},
            n_docs=int(data["n_docs"]),
            k1=float(data.get("k1", 1.5)),
            b=float(data.get("b", 0.75)),
        )


def build_bm25(
    doc_ids: Iterable[str],
    texts: Iterable[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> BM25Index:
    ids = list(doc_ids)
    text_list = list(texts)
    assert len(ids) == len(text_list)
    doc_len: list[int] = []
    postings: dict[str, list[tuple[int, int]]] = {}
    df: dict[str, int] = {}

    for idx, text in enumerate(text_list):
        counts = Counter(tokenize(text))
        doc_len.append(sum(counts.values()))
        for term, tf in counts.items():
            postings.setdefault(term, []).append((idx, tf))
            df[term] = df.get(term, 0) + 1

    avgdl = (sum(doc_len) / len(doc_len)) if doc_len else 0.0
    return BM25Index(
        doc_ids=ids,
        doc_len=doc_len,
        avgdl=avgdl,
        postings=postings,
        df=df,
        n_docs=len(ids),
        k1=k1,
        b=b,
    )
