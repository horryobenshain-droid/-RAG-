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
    assert results[0][1].retrieval_rank == 2
    assert "文件名与问题匹配" in results[0][1].reasons
    assert "代码符号与问题匹配" in results[0][1].reasons


def test_hybrid_rerank_distinguishes_modular_from_matrix_power() -> None:
    modular_power = Document(
        page_content=(
            "快速幂 ll qpow(ll a, ll b, ll mod) { "
            "while (b) { if (b & 1) res = res * a % mod; b >>= 1; } }"
        ),
        metadata={"original_file_name": "算法模板.pdf"},
    )
    matrix_power = Document(
        page_content=(
            "矩阵快速幂 using Matrix = vector<vector<ll>>; "
            "Matrix mpow(Matrix a, ll b, ll mod) { return a; }"
        ),
        metadata={"original_file_name": "算法模板.pdf"},
    )

    results = rerank_with_keywords(
        "请给出 C++ 模意义快速幂模板，只讲快速幂，并说明复杂度和边界条件。",
        [(matrix_power, 0.52), (modular_power, 0.39)],
        top_k=2,
    )

    assert results[0][0] is modular_power
    assert {"qpow", "mod", "快速幂"} <= set(results[0][1].matched_keywords)
