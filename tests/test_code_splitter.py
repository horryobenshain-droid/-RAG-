from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.splitter import split_documents


def test_code_splitter_adds_symbol_and_line_metadata() -> None:
    document = Document(
        page_content="""
#include <bits/stdc++.h>
using namespace std;

long long qmi(long long a, long long b, long long mod) {
    long long res = 1;
    while (b) {
        if (b & 1) res = res * a % mod;
        a = a * a % mod;
        b >>= 1;
    }
    return res;
}

int main() {
    cout << qmi(2, 10, 1000);
}
""".strip(),
        metadata={
            "document_type": "code",
            "extension": ".cpp",
            "file_name": "quick_power.cpp",
        },
    )

    chunks = split_documents([document], Settings(chunk_size=900))

    assert chunks
    qmi_chunk = next(chunk for chunk in chunks if chunk.metadata.get("symbol_name") == "qmi")
    assert qmi_chunk.metadata["language"] == "cpp"
    assert qmi_chunk.metadata["start_line"] >= 1
    assert qmi_chunk.metadata["end_line"] >= qmi_chunk.metadata["start_line"]
