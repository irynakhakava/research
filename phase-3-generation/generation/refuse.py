"""Правила отказа: секреты, не-документация, низкая уверенность."""

from __future__ import annotations

import re

# Секреты / персональные данные, которых не должно быть в ответе
_SECRET_RE = re.compile(
    r"("
    r"парол|password|passwd|secret|секрет|credential|"
    r"api[\s_-]?key|токен|token|"
    r"зарплат|salary|compensation|"
    r"ssn|паспорт"
    r")",
    re.IGNORECASE,
)

# Вопросы не про документацию (HR/личное)
_OUT_OF_SCOPE_RE = re.compile(
    r"("
    r"отпуск|vacation|больничн|"
    r"когда\s+\w+\s+выйд|"
    r"личный|личн(ая|ое|ые)\s+(жизнь|телефон|адрес)"
    r")",
    re.IGNORECASE,
)


def classify_query_refuse(question: str) -> str | None:
    """Вернуть reason или None, если по тексту вопроса отказ не обязателен."""
    q = (question or "").strip()
    if not q:
        return "empty_query"
    if _SECRET_RE.search(q):
        return "secret"
    if _OUT_OF_SCOPE_RE.search(q):
        return "out_of_scope"
    return None


def refuse_message(reason: str) -> str:
    messages = {
        "secret": (
            "Не могу ответить: секреты, пароли, ключи и персональные компенсации "
            "не выдаются из документации."
        ),
        "out_of_scope": (
            "Не могу ответить: вопрос не про внутреннюю документацию "
            "(личные/HR-сведения здесь не хранятся)."
        ),
        "empty_retrieval": (
            "Не могу ответить: в индексе нет фрагментов по этому вопросу."
        ),
        "low_confidence": (
            "Не могу уверенно ответить по найденным фрагментам — "
            "похоже, в документации нет прямого ответа."
        ),
        "not_in_context": (
            "Не могу ответить: в найденных фрагментах нет достаточных фактов."
        ),
        "empty_query": "Пустой вопрос.",
    }
    return messages.get(reason, "Не могу ответить по внутренней документации.")
