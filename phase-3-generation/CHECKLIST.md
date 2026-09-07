# Чеклист · Фаза 3 RAG generation

| Шаг | Описание | Статус |
|-----|----------|--------|
| 1. Ask pipeline | retrieve → refuse/generate → citations | done |
| 2. Extractive baseline | без LLM API | done |
| 3. CLI `run_ask.py` | JSON контракт `/ask` | done |
| 4. HTTP `POST /ask` | stdlib server | done |
| 5. Eval | refuse-rate, citation contract, grounded | done |
| 6. Tests | refuse / ACL / citations | done |
| 7. Tutorial | `docs/tutorials/03-rag-generation.md` | done |

## Definition of Done (фаза 3)

- [x] Вопрос даёт `answer` + `citations[]` с `path`/`url`  
- [x] Секреты и не-документация → `refuse` + nearest links  
- [x] ACL-фильтры фазы 2 действуют до генерации  
- [x] Eval-команда на gold-set  
- [x] HTTP `/ask` (тонкий; полный сервис — фаза 5)

**Не входит:** multi-turn, LLM-judge на 50 сэмплах, деплой.
