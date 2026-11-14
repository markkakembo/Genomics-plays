# Experimental Log (SAMPLE, synthetic numbers for demonstration only)

## Setup
- Models: Llama-3.2-1B-Instruct and Qwen2.5-1.5B-Instruct.
- Datasets: Natural Questions (open), TriviaQA, HotpotQA (distractor setting), 1,000 test questions each.
- Retriever: Contriever over a 2018 Wikipedia dump, top-5 passages.
- Metrics: Exact Match (EM), retrieval rate (share of queries that trigger retrieval), mean latency per query.
- Baselines: Closed-book (no retrieval), Always-RAG (retrieve for every query), FLARE-style active retrieval.
- Calibration: 500 held-out questions per dataset, target confident-error rate 10%.
- Hardware: a single NVIDIA T4 GPU, batch size 1, greedy decoding for the final answer.

## Observations
- CGR retrieves for 38% to 46% of queries depending on the dataset.
- On TriviaQA, CGR is slightly better than Always-RAG because retrieval is skipped on questions the model already answers correctly, avoiding distraction by irrelevant passages.
- On HotpotQA, CGR is 1.2 EM below Always-RAG; multi-hop questions often look confident but are wrong.
- Mean latency drops from 412 ms (Always-RAG) to 268 ms with CGR on Llama-3.2-1B.
- Using only token log-probability (no draft agreement) lowers EM by 1.0 to 1.8 points.
