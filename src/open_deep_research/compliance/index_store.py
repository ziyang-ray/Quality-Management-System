"""JSONL-backed persistence for compliance document chunks."""

import json
from pathlib import Path

from open_deep_research.compliance.schemas import DocumentChunk, IndexMetadata


CHUNKS_FILE = "chunks.jsonl"
METADATA_FILE = "index_metadata.json"


def write_index(index_dir: str | Path, chunks: list[DocumentChunk], metadata: IndexMetadata) -> None:
    """Write chunks and build metadata to disk."""

    target = Path(index_dir)
    target.mkdir(parents=True, exist_ok=True)
    with (target / CHUNKS_FILE).open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(chunk.model_dump_json(ensure_ascii=False) + "\n")
    with (target / METADATA_FILE).open("w", encoding="utf-8") as file:
        json.dump(metadata.model_dump(), file, ensure_ascii=False, indent=2)


def read_chunks(index_dir: str | Path) -> list[DocumentChunk]:
    """Read all indexed chunks from disk."""

    path = Path(index_dir) / CHUNKS_FILE
    if not path.exists():
        return []
    chunks: list[DocumentChunk] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(DocumentChunk.model_validate_json(line))
    return chunks


def read_metadata(index_dir: str | Path) -> IndexMetadata:
    """Read index metadata from disk if present."""

    path = Path(index_dir) / METADATA_FILE
    if not path.exists():
        return IndexMetadata()
    with path.open("r", encoding="utf-8") as file:
        return IndexMetadata.model_validate(json.load(file))

