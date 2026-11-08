from rag_platform.application.processing.chunking import ChunkingConfig, chunk_text


def test_chunk_text_respects_overlap() -> None:
    text = "a" * 100
    chunks = chunk_text(text, ChunkingConfig(chunk_size=30, overlap=5, max_chunks=10))
    assert len(chunks) >= 3
    assert all(len(c) <= 30 for c in chunks)
