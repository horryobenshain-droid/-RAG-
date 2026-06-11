from langchain_core.documents import Document

from app.rag.hybrid_retriever import rerank_with_keywords


def test_hybrid_rerank_boosts_keyword_and_symbol_matches() -> None:
    weak_vector_good_keyword = Document(
        page_content="long long qmi(long long a, long long b, long long mod) { return 1; }",
        metadata={"original_file_name": "快速幂模板.cpp", "symbol_name": "qmi"},
    )
    strong_vector_bad_keyword = Document(
        page_content="void dfs(int u) { }",
        metadata={"original_file_name": "dfs.cpp", "symbol_name": "dfs"},
    )

    results = rerank_with_keywords(
        "快速幂 qmi 怎么写",
        [(strong_vector_bad_keyword, 0.6), (weak_vector_good_keyword, 0.55)],
        top_k=2,
    )

    assert results[0][0] is weak_vector_good_keyword
    assert "qmi" in results[0][1].matched_keywords
    assert results[0][1].final_score > results[1][1].final_score
