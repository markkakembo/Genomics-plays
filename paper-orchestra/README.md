# paper-orchestra: a runnable PaperOrchestra pipeline

This project turns raw research materials (idea notes, an experiment log and results tables) into a LaTeX paper and a PDF. It follows the multi-agent pipeline in Google's paper:

> Song, Song, Pfister, Yoon. *PaperOrchestra: A Multi-Agent Framework for Automated AI Research Paper Writing.* arXiv:2604.05018 (Apr 2026).
> Paper: https://arxiv.org/abs/2604.05018 · Project page: https://yiwen-song.github.io/paper_orchestra/ · Official code: https://github.com/google-research/paper-orchestra (Apache-2.0)

The paper PDF is not included in this repository. Read it at https://arxiv.org/abs/2604.05018.

- `upstream/` holds the official code, unmodified. It only runs on Gemini or Vertex AI and was written for a dataset that hasn't been released yet.
- `paperorch/` is a re-implementation that works with **OpenAI, Anthropic or Gemini**. It also has an offline **mock** mode, so you can run the whole pipeline end to end without an API key. It reuses the official agent prompts word for word (it imports them from `upstream/`).

> ⚠️ This tool helps you draft. You are responsible for every claim, number and citation in the output (see the paper's ethics statement).

## Pipeline (paper Sec. 4)

| Step | Agent | Inputs | Outputs (in the run folder) |
|---|---|---|---|
| 1 | Outline | idea, experimental log, template.tex, guidelines.md | `outline.json` (plotting plan, intro/related-work search strategy, section plan with citation hints) |
| 2 ∥ 3 | Plotting | outline.plotting_plan, raw materials | `latex_writeup/figures/*.png`, `plotting_results.json` |
| 3 ∥ 2 | Literature Review | outline search strategy plus citation hints | `literature_agent_output/` (`references.bib`, `citation_map.json`, `registry.json`, `rejected_candidates.json`, `outline_v1.json`, `updated_template.tex` with Introduction and Related Work) |
| 4 | Section Writing | outline_v1, intro/related-work template, citation map, figures, log | `latex_writeup/raw_draft_paper.tex` |
| 5 | Content Refinement | draft, log, citation map, AgentReview reviewer | `content_refinement_workdir/` (reviews, versions v1..v3, worklog), then **`final_paper.tex` and `final_paper.pdf`** |

Steps 2 and 3 run in parallel. Literature discovery runs 10 workers at once, then each candidate is verified one at a time at about 1 request per second. A candidate is accepted only if all of these hold:
- its title matches a real paper with a fuzzy score above 70 (plus a 10-point bonus when the year matches)
- it has an abstract
- it was published before the research cutoff month

The writer must cite at least 90% of the verified papers. In refinement, a new version is kept if the Overall score goes up, or if it ties and the sub-score gains are at least as large as the drops. Otherwise the agent reverts to the previous version and stops. It runs at most 3 rounds.

## Quick start

```bash
cd /workspace/paper-orchestra
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# You need a LaTeX engine: TeX Live (latexmk/pdflatex) or tectonic (single binary, fetches packages on demand)
#   https://github.com/tectonic-typesetting/tectonic/releases

# 1) Offline dry run, no key needed (literature search still uses the real free APIs)
.venv/bin/python run.py --raw_materials examples/sample_project/raw_materials --out outputs/demo --provider mock

# 2) Real run with Gemini (the default provider). The key is read from ./.env (GEMINI_API_KEY=..., chmod 600,
#    git-ignored) via python-dotenv; it is never printed or logged.
.venv/bin/python run.py --raw_materials my_project/raw_materials                       # config.yaml: gemini-3.5-flash
.venv/bin/python run.py --config config.modest.yaml --raw_materials my_project/raw_materials   # ~15 calls, free-tier friendly

# Other providers: put OPENAI_API_KEY / ANTHROPIC_API_KEY in .env (or export it) and pass --provider openai|anthropic
# Optional: SEMANTIC_SCHOLAR_API_KEY (avoids the shared rate limit), OPENALEX_EMAIL
```

Useful flags: `--template iclr2025|cvpr2025|<folder>`, `--cutoff YYYY-MM`, `--no_plotting` (uses your own `figures/` instead of generating plots), `--max_reflections N`, `--max_search_tasks N` (caps searches to save cost). Model IDs for each role (writer, reflection, plotting, discovery) can be set in `config.yaml`. Check your provider's current model names.

## Input folder format

```
raw_materials/
  idea.md               # (or idea_dense.md / idea_sparse.md) problem, hypothesis, method, contributions
  experimental_log.md   # setup (models, datasets, baselines, metrics), raw numbers, observations
  tables/*.csv          # optional: added to the log as markdown tables
  notes/*.md            # optional: added to the idea
  figures/*.png|pdf     # optional: your own figures (used with --no_plotting)
```
The paper uses idea notes of roughly 600 words (sparse) or 1,100 words (dense, with equations), plus an experiment log that lists every number. More detail usually gives a better method section.

## Gemini notes (checked 2026-11-14 with `models.list()`)

- The paper's models (`gemini-3.1-pro-preview`, `gemini-3-flash-preview`) are not listed for this key, and `gemini-2.5-*` return 404. `gemini-3.5-flash` works and is the default in `config.yaml`.
- On the **free tier**, each model allows 5 requests per minute and 20 per day. Google Search grounding returned a quota error (429).
- How the code handles that:
  - Gemini calls are throttled to `GEMINI_MAX_RPM` (default 5). Set it to 0 on a paid key.
  - When grounding fails, it is switched off for the rest of the run, and keyword search fills in.
  - A daily-quota error stops the run immediately instead of retrying.
- `config.modest.yaml` is the free-tier profile:
  - `gemini-3.5-flash-lite` writes and `gemini-3.1-flash-lite` plots.
  - Literature candidates come from OpenAlex and arXiv keyword search, with no LLM discovery calls.
  - It allows 1 refinement round, 1 reviewer and no critic rounds.
  - The default `config.yaml` is the full paper-style setup. It needs a paid key (about 60–70 calls).

## Real Gemini run (2026-11-14): `outputs/sample_gemini_run/`

- Run with `config.modest.yaml` on the sample. It made 14 LLM calls and took about 2.7 minutes.
- Literature: 33 verified papers, 25 of them cited.
- Figures: 2 plots generated by Gemini.
- Review: Overall score went from 7 to 8, and the revision was kept.
- Output: an 8-page `final_paper.pdf`.
- **Check before trusting:** the model added a formal confidence formula (α, σ) and one number that isn't in the materials ("about 28 ms" overhead). That shows why the output needs a human check.
- `outputs/failed_gemini_run_quota/` is an earlier attempt that used up the daily quota of `gemini-3.5-flash`.

## What was tested (mock mode, on this machine)

- `outputs/sample_mock_run/`: the full 5-step run on the sample (ICLR template, plotting on).
  - **Literature:** real papers found and verified through OpenAlex and arXiv (45 papers in the last run, 42 cited in the intro and related work).
  - **Figures:** 2 matplotlib plots and 1 TikZ pipeline diagram.
  - **Tables:** booktabs tables built from the log.
  - **Refinement:** the accept/revert loop ran 3 times (5 to 6, then 2 ties).
  - **Output:** a 7-page `final_paper.pdf`.
- `outputs/test_cvpr_plotoff/`: the CVPR two-column template with `--no_plotting` and figures you supply (5-page PDF).
- The OpenAI request and response path was checked against a local fake server: a system prompt, an image, and the fallback when web search isn't available. The Anthropic and Gemini code paths were **not** run because there are no keys. Missing keys produce a clear error message.

Mock mode only proves that the steps hand off correctly. Its writing is template filler, and its reviewer scores with fixed rules. The **sample data is synthetic**.

## Differences from the paper / official code

| Area | Paper / upstream | Here |
|---|---|---|
| LLMs | Gemini-3.1-Pro (writing), Gemini-3-Flash with Google Search (discovery), gemini-3-pro-image (diagrams) | OpenAI, Anthropic or Gemini, with models set per role, plus offline mock |
| Candidate discovery | LLM with Google Search grounding | Gemini uses Google Search. OpenAI and Anthropic use their hosted web-search tools, and fall back to LLM recall if those aren't available. With `use_keyword_search: auto`, it also runs a direct OpenAlex/arXiv keyword search when there's no web search (and always in mock) |
| Verification | Semantic Scholar only | Semantic Scholar first, then arXiv, then OpenAlex (the free S2 tier returns HTTP 429 often). Keyword-search hits already include metadata and an abstract, so they skip the S2 lookup but still go through the cutoff and abstract checks |
| Diagrams | PaperBanana image generation (Gemini image model) | The LLM writes **TikZ**, compiled with LaTeX; Graphviz DOT is the fallback if `dot` is installed. Plots match the paper: LLM-written matplotlib code, a critic loop and a caption |
| PaperBanana few-shot retrieval and style guides | Uses the separate PaperBanana reference set | Skipped (the data isn't in the repo). Uses the planner, stylist, critic and caption prompts only |
| Plot code execution | `exec` in-process | Runs in a subprocess with a 120 s timeout. It is still LLM-written code, so use a container for untrusted setups |
| Refinement input | Sends the PDF file to Gemini | Sends page PNGs to vision models. The reviewer reads the PDF text |
| Citation guard | Prompt-only | Also removes any `\cite` key that isn't in the verified pool |
| Evaluators (citation F1, SxS, lit-review autoraters, ScholarPeer) | `upstream/autoraters/` (Gemini) | Not re-implemented. Use upstream with a Gemini key |
| Batch over PaperWritingBench | `upstream/methods/*` batch runner | Single paper at a time. The benchmark dataset isn't released yet |

## Running the official code instead

`upstream/README.md` covers this: conda env, `.env` with `GEMINI_API_KEY` (or Vertex), and `SEMANTIC_SCHOLAR_API_KEY`. Then run:
`python paper_writing_cli.py --raw_materials_dir <dir with idea_sparse.md + experimental_log.md> --latex_template_dir templates/iclr2025 --output_dir out --use_plotting true`.
It needs `pdflatex` and `bibtex`. Diagrams also need Gemini image models.

## Cost and time (paper App. B)

A full paper takes about 60 to 70 LLM calls and averaged about 40 minutes with Gemini. The calls break down as:
- Outline: 1
- Literature: 20 to 30
- Plotting: 20 to 30
- Section writing: 1
- Refinement: 5 to 7

Each run logs every call to `llm_calls.jsonl`. You'll find a summary in `run_summary.json`.

## License
Apache-2.0 (see `LICENSE` and `NOTICE`). `upstream/` is © Google LLC. The paper itself is CC BY 4.0 on arXiv.
