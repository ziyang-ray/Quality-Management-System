"""Build the local compliance JSONL index from official and internal files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from open_deep_research.compliance.chunking import chunk_elements
from open_deep_research.compliance.document_loader import SUPPORTED_EXTENSIONS, load_file
from open_deep_research.compliance.index_store import write_index
from open_deep_research.compliance.schemas import DocumentChunk, IndexMetadata, SourceType
from open_deep_research.configuration import Configuration


def main() -> int:
    config = Configuration()
    parser = argparse.ArgumentParser(description="Build a local compliance evidence index.")
    parser.add_argument("--official-docs", default=config.official_docs_path)
    parser.add_argument("--internal-docs", default=config.internal_docs_path)
    parser.add_argument("--index-dir", default=config.compliance_index_path)
    args = parser.parse_args()

    chunks: list[DocumentChunk] = []
    metadata = IndexMetadata(
        source_roots={
            "standard": str(Path(args.official_docs).resolve()),
            "internal": str(Path(args.internal_docs).resolve()),
        }
    )

    for root, source_type in [
        (Path(args.official_docs), "standard"),
        (Path(args.internal_docs), "internal"),
    ]:
        _load_root(root, source_type, chunks, metadata)

    metadata.total_chunks = len(chunks)
    write_index(args.index_dir, chunks, metadata)
    print(f"Wrote {metadata.total_chunks} chunks to {Path(args.index_dir).resolve()}")
    print(f"Indexed files: {metadata.total_files_indexed}/{metadata.total_files_seen}")
    print(f"Skipped files: {len(metadata.skipped_files)}")
    return 0


def _load_root(root: Path, source_type: SourceType, chunks: list[DocumentChunk], metadata: IndexMetadata) -> None:
    if not root.exists():
        metadata.skipped_files.append({"path": str(root), "reason": "root_not_found"})
        return

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        metadata.total_files_seen += 1
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            metadata.skipped_files.append({"path": str(path), "reason": f"unsupported_extension:{path.suffix}"})
            continue
        try:
            elements = load_file(path, source_type)
            file_chunks = chunk_elements(elements)
            if not file_chunks:
                metadata.skipped_files.append({"path": str(path), "reason": "no_extractable_text"})
                continue
            chunks.extend(file_chunks)
            metadata.total_files_indexed += 1
        except Exception as exc:
            metadata.skipped_files.append({"path": str(path), "reason": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    raise SystemExit(main())
