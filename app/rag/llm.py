import re
from typing import Literal

import requests
from langchain_core.documents import Document

from app.core.config import Settings

AnswerMode = Literal["strict", "augmented"]

RESPONSE_STYLE_RULES = """输出要求：
- 只回答用户当前提出的问题，不扩展无关算法、模板或背景知识。
- 回答前先判断每个检索片段是否直接支持当前问题；仅有相同关键词不代表相关。
- 忽略主题相近但对象不同的片段，不得为了迎合检索片段而改变用户的问题主题。
- 先给结论，再给必要说明；默认使用不超过 5 个简短小节，避免大段堆砌。
- 不重复标题、提示语、结论或段落。
- 代码必须放在带语言标识的 Markdown 代码块中，例如 ```cpp。
  不要在正文中裸写 C++ 泛型、比较表达式或残缺代码。
- 用户要求代码时，只给与问题直接相关且结构完整的模板，并说明复杂度和关键边界条件。
- 不确定的信息要明确说明，不要用残缺伪代码填充答案。"""

STRICT_SYSTEM_PROMPT = f"""你是一个严谨的本地知识库问答助手。
你的任务是基于检索片段回答用户问题，并尽量降低幻觉。

规则：
1. 只能使用检索片段中明确出现的信息作答。
2. 如果检索片段不足以回答问题，请回答“当前知识库中没有足够信息回答这个问题”。
3. 不要编造文件、页码、实验结果、代码行为或论文结论。
4. 回答应简洁、专业，默认使用简体中文。
5. 在答案末尾列出引用来源，例如：引用：source 1, source 3。
6. 如果检索片段包含代码，保留关键函数名、变量名和边界条件。

{RESPONSE_STYLE_RULES}
"""

AUGMENTED_SYSTEM_PROMPT = f"""你是一个知识库增强问答助手。
你的任务是优先基于检索片段回答用户问题；当检索片段不足时，必须使用你的通用知识补充。

规则：
1. 如果检索片段能回答问题，请优先引用检索片段，并在答案末尾列出引用来源。
2. 如果检索片段不足，不能只回答“当前知识库中没有足够信息回答这个问题”。
3. 如果检索片段不足，可以在开头说明一次“以下补充基于模型通用知识”，答案中不得重复该声明。
4. 不要把模型通用知识伪装成知识库内容。
5. 回答应简洁、专业，默认使用简体中文。
6. 如果答案同时使用了知识库和通用知识，请分清哪些来自知识库，哪些是补充说明。
7. 如果用户询问算法模板或代码，即使检索片段不完整，也要基于通用知识给出完整说明。
8. 只有严格知识库模式才允许直接拒答；当前是知识库增强模式，必须尽力补充。

{RESPONSE_STYLE_RULES}
"""

AUGMENTED_USER_GUIDE = """当前回答模式：知识库增强。
请直接回答当前问题。优先使用检索片段；片段不足时使用模型通用知识补充，来源声明最多出现一次。
先排除只共享关键词但没有直接回答当前问题的片段，禁止改变问题主题来迎合片段。
禁止重复提示语、输出无关内容或给出未放入 Markdown 代码块的代码。"""

_AUGMENTED_NOTICE_PATTERN = re.compile(
    r"(?m)^[ \t]*[\[【]?\s*知识库资料不足[，,]\s*以下为模型通用知识补充\s*[\]】]?[。.]?[ \t]*$"
)

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
    if settings.llm_provider == "ollama":
        return _generate_with_ollama(question, context, settings, answer_mode)

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
        input=_build_openai_input(question, context_text, answer_mode),
        reasoning={"effort": "low"},
        text={"verbosity": "medium"},
    )
    return _clean_model_answer(response.output_text)


def _build_openai_input(question: str, context_text: str, answer_mode: AnswerMode) -> str:
    if answer_mode == "augmented":
        return f"{AUGMENTED_USER_GUIDE}\n\n检索片段：\n{context_text}\n\n用户问题：{question}"
    return f"检索片段：\n{context_text}\n\n用户问题：{question}"


def _generate_with_ollama(
    question: str,
    context: str,
    settings: Settings,
    answer_mode: AnswerMode,
) -> str:
    prompt = STRICT_SYSTEM_PROMPT if answer_mode == "strict" else AUGMENTED_SYSTEM_PROMPT
    context_text = context or "当前没有检索到可用知识库片段。"
    payload = {
        "model": settings.ollama_chat_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": _build_ollama_user_message(question, context_text, answer_mode),
            },
        ],
        "options": {
            "temperature": settings.ollama_temperature,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
            "top_p": settings.ollama_top_p,
            "repeat_penalty": settings.ollama_repeat_penalty,
        },
    }

    chat_url = _ollama_chat_url(settings.ollama_base_url)
    try:
        response = requests.post(
            chat_url,
            json=payload,
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        msg = (
            "调用 Ollama 失败，请确认 Ollama 已启动且模型已拉取。\n"
            f"地址：{chat_url}\n"
            f"模型：{settings.ollama_chat_model}\n"
            f"错误：{exc}"
        )
        raise ValueError(msg) from exc

    data = response.json()
    content = data.get("message", {}).get("content")
    if not content:
        msg = "Ollama 未返回有效回答内容。"
        raise ValueError(msg)
    return _clean_model_answer(str(content))


def _build_ollama_user_message(question: str, context_text: str, answer_mode: AnswerMode) -> str:
    if answer_mode == "augmented":
        return f"{AUGMENTED_USER_GUIDE}\n\n检索片段：\n{context_text}\n\n用户问题：{question}"
    return f"检索片段：\n{context_text}\n\n用户问题：{question}"


def _ollama_chat_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/api"):
        return f"{normalized}/chat"
    return f"{normalized}/api/chat"


def _clean_model_answer(content: str) -> str:
    notice_seen = False

    def replace_notice(_: re.Match[str]) -> str:
        nonlocal notice_seen
        if notice_seen:
            return ""
        notice_seen = True
        return "> 以下补充基于模型通用知识。"

    cleaned = _AUGMENTED_NOTICE_PATTERN.sub(replace_notice, content.strip())
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


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
