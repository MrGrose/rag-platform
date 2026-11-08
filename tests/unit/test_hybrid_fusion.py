from uuid import uuid4

from rag_platform.application.retrieval.hybrid import fuse_hits


def test_fuse_hits_merges_vector_and_lexical() -> None:
    c1 = uuid4()
    c2 = uuid4()
    d = uuid4()
    kb = uuid4()
    fused = fuse_hits(
        [(c1, d, kb, "vector hit", 0.9), (c2, d, kb, "weak vector", 0.1)],
        [(c2, d, kb, "lexical hit", 1.0)],
        limit=2,
    )
    assert len(fused) == 2
    assert {hit.chunk_id for hit in fused} == {c1, c2}
