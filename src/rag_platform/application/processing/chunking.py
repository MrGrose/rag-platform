from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    chunk_size: int
    overlap: int
    max_chunks: int


def chunk_text(text: str, config: ChunkingConfig) -> list[str]:
    if not text:
        return []
    size = max(config.chunk_size, 1)
    overlap = min(max(config.overlap, 0), size - 1)
    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text) and len(chunks) < config.max_chunks:
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start += step
    return chunks
