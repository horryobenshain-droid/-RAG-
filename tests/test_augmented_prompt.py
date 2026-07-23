from app.rag.llm import AUGMENTED_SYSTEM_PROMPT, _build_openai_input


def test_augmented_prompt_requires_model_prior_when_context_is_incomplete() -> None:
    assert "必须使用你的通用知识补充" in AUGMENTED_SYSTEM_PROMPT
    assert "不能只回答" in AUGMENTED_SYSTEM_PROMPT
    assert "当前是知识库增强模式" in AUGMENTED_SYSTEM_PROMPT


def test_augmented_openai_input_adds_mode_specific_guidance() -> None:
    prompt_input = _build_openai_input(
        question="解释一下最短路径算法",
        context_text="当前没有检索到可用知识库片段。",
        answer_mode="augmented",
    )

    assert "当前回答模式：知识库增强" in prompt_input
    assert "来源声明最多出现一次" in prompt_input
    assert "禁止改变问题主题" in prompt_input
    assert "Markdown 代码块" in prompt_input
    assert "解释一下最短路径算法" in prompt_input


def test_strict_openai_input_keeps_knowledge_base_only_shape() -> None:
    prompt_input = _build_openai_input(
        question="解释一下最短路径算法",
        context_text="当前没有检索到可用知识库片段。",
        answer_mode="strict",
    )

    assert "当前回答模式：知识库增强" not in prompt_input
    assert "用户问题：解释一下最短路径算法" in prompt_input
