# Da Vinci's Poet: architecture

Browser -> FastAPI -> Crossref discovery -> DOI normalization/deduplication -> evidence ledger -> deterministic dossier or optional LLM synthesis -> source-ID check -> human review.

## Boundaries
- Crossref is bibliographic discovery, not a systematic-review database.
- DOI values are normalized, not independently resolved.
- Abstracts are source-provided, not checked against full text.
- LLM citation-ID validation is not semantic entailment.
- No persistent user accounts, manuscript approval, or full-text screening yet.

## Original vs custom
Inspired by [Google PaperOrchestra](https://github.com/google-research/paper-orchestra), which describes outlining, literature, plotting, writing, and refinement agents. This is a narrower independent Python implementation with no source code copied from Google.

## Deployment
Use Python 3.11+, install requirements, run `uvicorn app.main:app --host 0.0.0.0 --port 8080`. Build with Dockerfile. Google Cloud Run deployment can use `gcloud run deploy researchorchestra --source . --region us-central1 --no-allow-unauthenticated`. Set secrets via a managed secrets service. Cloud Run IAM may not provide seamless browser login. Do not expose the prototype publicly without identity, quotas, cost limits and abuse protection. Never upload private patient records or confidential lab data.
