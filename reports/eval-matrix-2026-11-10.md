# Retrieval matrix 2026-11-10

Corpus: 28 documents (including 16 distractors), 18 answerable questions.
Metrics are retrieval-only: no LLM call, reranker limited to five hits.

| Embeddings | Retrieval | Reranker | hit@1 | hit@5 | MRR@5 | p50, ms |
|------------|-----------|----------|-------|-------|-------|---------|
| fake | vector | off | 0.111 | 0.111 | 0.139 | 3.3 |
| fake | vector | bge_reranker | 0.944 | 1.000 | 0.972 | 2762.4 |
| fake | hybrid | off | 0.111 | 0.111 | 0.139 | 4.9 |
| fake | hybrid | bge_reranker | 0.944 | 1.000 | 0.972 | 2753.3 |
| bge_m3 | vector | off | 0.944 | 1.000 | 0.972 | 78.2 |
| bge_m3 | vector | bge_reranker | 0.944 | 1.000 | 0.972 | 2780.7 |
| bge_m3 | hybrid | off | 0.944 | 1.000 | 0.972 | 56.0 |
| bge_m3 | hybrid | bge_reranker | 0.944 | 1.000 | 0.972 | 2874.5 |
