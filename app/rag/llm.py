from langchain_core.documents import Document

from app.core.config import Settings

SYSTEM_PROMPT = """你是一个严谨的本地知识库问答助手。
你的任务是基于检索片段回答用户问题，并尽量降低幻觉。

规则：
1. 只能使用检索片段中明确出现的信息作答。
2. 如果检索片段不足以回答问题，请回答“当前知识库中没有足够信息回答这个问题”。
3. 不要编造文件、页码、实验结果、代码行为或论文结论。
4. 回答应简洁、专业，默认使用简体中文。
5. 在答案末尾列出引用来源，例如：引用：source 1, source 3。
"""


def build_context(documents: list[Document]) -> str:
    blocks = []
    for index, document in enumerate(documents, start=1):
        file_name = document.metadata.get("original_file_name", "unknown")
        page = document.metadata.get("page")
        chunk_id = document.metadata.get("chunk_id", "unknown")
        location = f"{file_name}"
        if page is not None:
            location += f"，第 {int(page) + 1} 页"
        location += f"，chunk {chunk_id}"
        blocks.append(f"[source {index}: {location}]\n{document.page_content}")
    return "\n\n".join(blocks)


def generate_answer(question: str, documents: list[Document], settings: Settings) -> str:
    if not documents:
        return "当前知识库中没有检索到相关内容，请先上传并入库文档。"

    context = build_context(documents)
    if settings.llm_provider == "openai":
        return _generate_with_openai(question, context, settings)

    return _generate_demo_answer(question, documents)


def _generate_with_openai(question: str, context: str, settings: Settings) -> str:
    if not settings.openai_api_key:
        msg = "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
        raise ValueError(msg)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_chat_model,
        instructions=SYSTEM_PROMPT,
        input=f"检索片段：\n{context}\n\n用户问题：{question}",
        reasoning={"effort": "low"},
        text={"verbosity": "medium"},
    )
    return response.output_text


def _generate_demo_answer(question: str, documents: list[Document]) -> str:
    preview = "\n\n".join(
        f"[source {index}] {document.page_content.strip()[:360]}"
        for index, document in enumerate(documents, start=1)
    )
    return (
        "当前运行在 demo 模式，未调用真实大模型。\n\n"
        f"问题：{question}\n\n"
        "下面是向量检索命中的相关片段，可用于验证 RAG 检索链路：\n"
        f"{preview}"
    )
