from typing import Literal

from langchain_core.documents import Document

from app.core.config import Settings

AnswerMode = Literal["strict", "augmented"]

STRICT_SYSTEM_PROMPT = """你是一个严谨的本地知识库问答助手。
你的任务是基于检索片段回答用户问题，并尽量降低幻觉。

规则：
1. 只能使用检索片段中明确出现的信息作答。
2. 如果检索片段不足以回答问题，请回答“当前知识库中没有足够信息回答这个问题”。
3. 不要编造文件、页码、实验结果、代码行为或论文结论。
4. 回答应简洁、专业，默认使用简体中文。
5. 在答案末尾列出引用来源，例如：引用：source 1, source 3。
6. 如果用户询问算法模板或代码，请优先按“适用场景、核心思路、代码模板、复杂度、注意事项”组织回答。
7. 如果检索片段包含代码，保留关键函数名、变量名和边界条件。
"""

AUGMENTED_SYSTEM_PROMPT = """你是一个知识库增强问答助手。
你的任务是优先基于检索片段回答用户问题；当检索片段不足时，可以使用你的通用知识补充。

规则：
1. 如果检索片段能回答问题，请优先引用检索片段，并在答案末尾列出引用来源。
2. 如果检索片段不足，请明确说明“知识库资料不足，以下为模型通用知识补充”。
3. 不要把模型通用知识伪装成知识库内容。
4. 回答应简洁、专业，默认使用简体中文。
5. 如果答案同时使用了知识库和通用知识，请分清哪些来自知识库，哪些是补充说明。
6. 如果用户询问算法模板或代码，请优先按“适用场景、核心思路、代码模板、复杂度、注意事项”组织回答。
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


def generate_answer(
    question: str,
    documents: list[Document],
    settings: Settings,
    answer_mode: AnswerMode,
) -> str:
    if not documents and answer_mode == "strict":
        return "当前知识库中没有检索到相关内容，请先上传并入库文档。"

    context = build_context(documents)
    if settings.llm_provider == "openai":
        return _generate_with_openai(question, context, settings, answer_mode)

    return _generate_demo_answer(question, documents, answer_mode)


def _generate_with_openai(
    question: str,
    context: str,
    settings: Settings,
    answer_mode: AnswerMode,
) -> str:
    if not settings.openai_api_key:
        msg = "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
        raise ValueError(msg)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    prompt = STRICT_SYSTEM_PROMPT if answer_mode == "strict" else AUGMENTED_SYSTEM_PROMPT
    context_text = context or "当前没有检索到可用知识库片段。"
    response = client.responses.create(
        model=settings.openai_chat_model,
        instructions=prompt,
        input=f"检索片段：\n{context_text}\n\n用户问题：{question}",
        reasoning={"effort": "low"},
        text={"verbosity": "medium"},
    )
    return response.output_text


def _generate_demo_answer(
    question: str,
    documents: list[Document],
    answer_mode: AnswerMode,
) -> str:
    if not documents and answer_mode == "augmented":
        return (
            "当前运行在 demo 模式，未调用真实大模型。\n\n"
            f"问题：{question}\n\n"
            "知识库没有召回片段；增强模式需要真实 LLM 才能使用通用知识补充。"
        )

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
