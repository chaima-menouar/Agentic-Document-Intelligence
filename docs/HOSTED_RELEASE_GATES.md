# Hosted release quality gates

Do not label a hosted build production-ready based only on HTTP 200, verified citations, or a passing unit test.

## Baseline to compare
The documented 13 October 2026 patched pilot recorded **4/15** relevant answers, **5/5** safe abstentions and **19/20** successful HTTP requests. One HTTP 409 occurred after upload because sessions are process-local across Vercel instances. These are manually reviewed pilot counts, not population estimates.

## Required release checks
- [ ] Run the same 20-question real-PDF pilot against the candidate deployment.
- [ ] Manually review all 15 answerable questions against reference PDFs and pages; report correct/incorrect individually.
- [ ] Report safe abstention separately for all five unsupported questions.
- [ ] Report HTTP 409 and other failures separately from answer accuracy.
- [ ] Include question-level regressions for similar numerical values, tables, headings and answer truncation.
- [ ] Test OCR on scanned PDF and multi-document questions.
- [ ] Test upload rejection at documented size limits, including user-facing explanation.
- [ ] Test session continuity after a restart and with requests routed to separate instances.
- [ ] Preserve privacy: no sensitive uploaded documents or session data in CI logs.

## Deployment decision
For multi-instance hosting, a shared durable session registry and durable document/index storage are required; a local Python dictionary or process filesystem is not sufficient. Until implemented and tested, label hosted workspaces temporary and ask users to export their work. Do not claim persistence or multi-instance reliability.

## Reproduction
Use `python scripts/run_hosted_pilot.py --output /tmp/adi-pilot` as documented in `evaluation/hosted_pilot/README.md`. The runner output still needs manual relevance judgment. Compare the candidate against the same source corpus and question set; publish both positive and negative results.
