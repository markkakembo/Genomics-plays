# Confidence-Gated Retrieval for Small Language Models

> SAMPLE INPUT. This is a made-up research idea with synthetic numbers, written only to
> demonstrate the PaperOrchestra pipeline. It is not a real study.

## Problem Statement
Retrieval-augmented generation (RAG) improves factual accuracy of language models, but most
pipelines retrieve for every query. For small language models (under 3B parameters) running on
limited hardware, retrieval roughly doubles latency, and irrelevant passages can distract the model
and lower accuracy on questions it could already answer from its own parameters.

## Core Hypothesis
A small model's own uncertainty is a cheap and reliable signal for when retrieval is needed. If we
retrieve only when the model is unsure, we can keep most of the accuracy gains of always-on RAG
while skipping retrieval for a large share of queries.

## Proposed Method: Confidence-Gated Retrieval (CGR)
1. **Draft pass**: the model answers the question closed-book and we record token-level
   probabilities of the drafted answer.
2. **Confidence score**: we combine the mean token log-probability with the agreement rate of
   three sampled drafts into a single score between 0 and 1.
3. **Calibrated gate**: a threshold on the score is chosen on a held-out split with split-conformal
   calibration so that the rate of confidently wrong answers stays below a target level.
4. **Retrieve and answer**: only for queries below the threshold, we retrieve the top-5 passages
   with a dense retriever and regenerate the answer conditioned on them.

## Positioning / related directions
- Adaptive retrieval that decides when to retrieve during generation
- Uncertainty estimation and calibration for language model outputs
- Conformal prediction for selective answering and abstention
- Efficient inference for small language models on edge devices

## Expected Contribution
- A training-free gate that works with any small model and any retriever.
- A calibration procedure with an explicit, tunable error target.
- Evidence that selective retrieval can match always-on RAG at lower cost.
