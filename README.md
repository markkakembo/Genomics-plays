# Da Vinci's Poet

**Research software at the intersection of biochemistry, bioinformatics and evidence-grounded AI.**

> Turning scientific questions into traceable evidence.

## First product: ResearchOrchestra Literature Explorer (v0.1)

A small, open-source research prototype that searches scholarly metadata, builds a DOI-linked evidence inventory, and generates a cautious literature dossier. It is **not** a systematic review engine, autonomous scientist, or publication-ready manuscript generator.

**What works**
- Crossref scholarly search, DOI normalization and deduplication
- Source records explicitly labeled `abstract_available` or `metadata_only`
- Deterministic Markdown dossier without an API key
- Optional AI-assisted synthesis, restricted to known citation IDs
- FastAPI endpoint, browser UI, Markdown download and Docker container
- Unit tests and architecture documentation

**Scientific boundaries:** DOI strings are not resolved independently; Crossref abstracts are not checked against full texts; source-ID validation does not establish that a claim is scientifically supported. Human review remains mandatory.

## Quickstart

Requires Python 3.11+.

```bash
git clone https://github.com/markkakembo/Genomics-plays.git
cd Genomics-plays
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://localhost:8000**. Optional configuration is documented in `.env.example`.

```bash
python -m pytest -q
docker build -t da-vincis-poet .
docker run --rm -p 8080:8080 da-vincis-poet
```

For cloud deployment, see [architecture and deployment notes](docs/ARCHITECTURE.md). Public hosting requires identity controls, request limits, abuse protection and secret management; **the demo has not been deployed as a hosted service**.

## Projects

Small, tested builds, each in its own folder with its own README, tests and sources.

- [Channel Spillover Lab](projects/2026-11-18-channel-spillover-lab/): an educational simulation of channel spillover in multiplexed images.
- [bb5verify](projects/2026-11-15-bb5verify/): re-runs the BB(5) champion Turing machine with two independent simulators and rebuilds the enumerate-and-decide method at small scale.
- [collapse-lab](projects/2026-11-15-collapse-lab/): theory-checked toy simulations of model collapse, replace versus accumulate.

## Research notes

- [DreaMS: learning molecular representations from unannotated mass spectra](docs/research/DREAMS.md) — an attributed review of Bushuiev et al., with reported results, limitations and separate commentary. No original experiments or benchmark reproduction.

## Research direction

Biomarker discovery and validation · nephrology and chronic kidney disease · LC-MS metabolomics/lipidomics · scientific reproducibility · evidence retrieval · applied bioinformatics.

## Credit and independence

Inspired conceptually by [Google Research's PaperOrchestra](https://github.com/google-research/paper-orchestra) and the publication by Song et al. (2026), [arXiv:2604.05018](https://arxiv.org/abs/2604.05018). This project is an independent, narrower implementation; **not a fork, not affiliated with Google, and does not reuse its source code**.

## Roadmap

1. PubMed retrieval and bibliographic validation
2. Passage-level evidence provenance and claim audits
3. Researcher review and persistent projects
4. Reproducible statistical analyses, figures and manuscript exports

Author: [Mark Kakembo](https://github.com/markkakembo). See [profile README draft](docs/PROFILE_README.md) for professional background and related work.

**License:** MIT (see [LICENSE](LICENSE)).