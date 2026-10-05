# Data

The project uses three public research datasets for different evaluation goals.

## Datasets

### QASPER — primary document QA benchmark
- Source: AllenAI / Hugging Face
- Purpose: document question answering, evidence retrieval, citation evaluation
- License: CC BY 4.0
- We preserve the official train/validation/test splits.

### SciFact — claim verification benchmark
- Source: AllenAI
- Purpose: claim-level SUPPORT / CONTRADICT evidence verification
- Claims/evidence annotations are CC BY 4.0; the abstract corpus comes from S2ORC and has its own attribution terms.
- We keep the official train/dev/test files and corpus.

### HotpotQA — agentic / multi-hop stress test
- Source: HotpotQA / Hugging Face
- Purpose: multi-document and additional-retrieval evaluation
- License: CC BY-SA 4.0
- To keep the academic project manageable, the default collector stores a deterministic 10,000-example subset of the distractor training split.

## Reproducibility

Large external datasets are **not committed directly to Git history**. They are collected reproducibly with:

```bash
pip install -r requirements-data.txt
python scripts/prepare_datasets.py --output data/external --hotpot-size 10000
```

The script writes a `manifest.json` recording source, split sizes, licenses, and the random seed.

GitHub Actions also runs the collector and uploads the prepared dataset bundle as an artifact.
