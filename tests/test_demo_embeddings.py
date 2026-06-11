from app.rag.embeddings import HashEmbeddings


def test_hash_embeddings_are_deterministic() -> None:
    embeddings = HashEmbeddings(dimensions=32)

    first = embeddings.embed_query("retrieval augmented generation")
    second = embeddings.embed_query("retrieval augmented generation")

    assert first == second
    assert len(first) == 32
