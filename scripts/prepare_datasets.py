"""Collect and normalize the public datasets used by the project.

The collector intentionally keeps external datasets out of Git history while
making the exact data preparation reproducible. It prepares:
  * QASPER official splits
  * SciFact official corpus and claim splits
  * A deterministic HotpotQA distractor subset for agentic stress testing
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

import requests
from datasets import Dataset, DatasetDict, load_dataset

SCIFACT_TARBALL = (
    "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
)


def _write_parquet_splits(dataset: DatasetDict, destination: Path) -> dict[str, int]:
    destination.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for split_name, split in dataset.items():
        output = destination / f"{split_name}.parquet"
        split.to_parquet(output)
        counts[split_name] = len(split)
    return counts


def collect_qasper(output: Path) -> dict:
    dataset = load_dataset("allenai/qasper")
    counts = _write_parquet_splits(dataset, output / "qasper")
    return {
        "name": "QASPER",
        "source": "https://huggingface.co/datasets/allenai/qasper",
        "license": "CC BY 4.0",
        "splits": counts,
    }


def _download(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)


def collect_scifact(output: Path) -> dict:
    destination = output / "scifact"
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        archive_path = temp_dir_path / "data.tar.gz"
        _download(SCIFACT_TARBALL, archive_path)

        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(temp_dir_path)

        candidates = [
            temp_dir_path / "data",
            temp_dir_path,
        ]
        source_dir = next(
            (candidate for candidate in candidates if (candidate / "corpus.jsonl").exists()),
            None,
        )
        if source_dir is None:
            raise RuntimeError("Could not locate extracted SciFact data files.")

        core_files = [
            "corpus.jsonl",
            "claims_train.jsonl",
            "claims_dev.jsonl",
            "claims_test.jsonl",
        ]
        for filename in core_files:
            shutil.copy2(source_dir / filename, destination / filename)

    counts: dict[str, int] = {}
    for filename in ["claims_train.jsonl", "claims_dev.jsonl", "claims_test.jsonl"]:
        with (destination / filename).open("r", encoding="utf-8") as file:
            counts[filename.removeprefix("claims_").removesuffix(".jsonl")] = sum(
                1 for _ in file
            )

    with (destination / "corpus.jsonl").open("r", encoding="utf-8") as file:
        corpus_count = sum(1 for _ in file)

    return {
        "name": "SciFact",
        "source": "https://github.com/allenai/scifact",
        "license": {
            "claims_and_annotations": "CC BY 4.0",
            "corpus": "S2ORC / ODC-By 1.0 attribution terms",
        },
        "splits": counts,
        "corpus_documents": corpus_count,
    }


def collect_hotpotqa(output: Path, size: int, seed: int) -> dict:
    if size <= 0:
        raise ValueError("--hotpot-size must be greater than zero.")

    train: Dataset = load_dataset(
        "hotpotqa/hotpot_qa",
        "distractor",
        split="train",
    )
    requested_size = min(size, len(train))
    subset = train.shuffle(seed=seed).select(range(requested_size))

    destination = output / "hotpotqa"
    destination.mkdir(parents=True, exist_ok=True)
    subset.to_parquet(destination / f"distractor_train_{requested_size}.parquet")

    return {
        "name": "HotpotQA",
        "source": "https://huggingface.co/datasets/hotpotqa/hotpot_qa",
        "license": "CC BY-SA 4.0",
        "config": "distractor",
        "split": "train",
        "examples": requested_size,
        "seed": seed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare project research datasets.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/external"),
        help="Directory where prepared external datasets are stored.",
    )
    parser.add_argument(
        "--hotpot-size",
        type=int,
        default=10_000,
        help="Number of HotpotQA distractor training examples to keep.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used for deterministic HotpotQA sampling.",
    )
    parser.add_argument(
        "--skip-hotpot",
        action="store_true",
        help="Prepare only QASPER and SciFact.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = {
        "format_version": 1,
        "datasets": [
            collect_qasper(args.output),
            collect_scifact(args.output),
        ],
    }

    if not args.skip_hotpot:
        manifest["datasets"].append(
            collect_hotpotqa(args.output, args.hotpot_size, args.seed)
        )

    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Prepared datasets in: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
