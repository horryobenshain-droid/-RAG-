# 架构说明

## RAG 流程

1. 用户通过 Streamlit 或 FastAPI 上传本地文件。
2. 后端保存文件并计算 SHA256 哈希。
3. Loader 将 PDF、Word、文本或代码文件转换为 LangChain `Document`。
4. Splitter 将文档切分为 chunk，并写入 `document_id`、页码、文件名、入库时间等元数据。
5. Embedding Provider 将 chunk 转成向量。
6. Chroma 将向量和元数据持久化到 `data/chroma/`。
7. 文档注册表将文件级生命周期信息写入 `data/registry.json`。
8. 用户提问时，Retriever 召回 top-k 片段并返回相关度分数。
9. Answer Policy 根据回答模式选择严格知识库 Prompt 或增强 Prompt。
10. LLM 根据检索片段、Prompt 和回答模式生成回答。
11. API 返回回答、来源、相关度、耗时、模型配置和答案依据。

## 模块

- `app/api`：HTTP 路由和请求/响应模型。
- `app/core/config.py`：环境变量、目录路径和 provider 配置。
- `app/core/files.py`：文件名清洗、上传保存、哈希计算。
- `app/core/registry.py`：本地 JSON 文档注册表。
- `app/loaders/local_loader.py`：PDF、Word、文本和代码文件加载。
- `app/rag/embeddings.py`：demo 哈希向量与 OpenAI Embeddings 适配。
- `app/rag/embeddings.py`：demo 哈希向量、OpenAI Embeddings、本地 HuggingFace Embeddings。
- `app/rag/vectorstore.py`：Chroma 初始化、检索、删除和重置。
- `app/rag/llm.py`：Prompt 构造和 OpenAI Responses API 调用。
- `app/rag/service.py`：入库、问答和知识库管理业务逻辑。
- `ui/streamlit_app.py`：简体中文前端界面。

## Provider 模式

`demo` 模式用于本地开发，不需要 API Key：

- Embedding：确定性哈希向量。
- LLM：返回召回片段，验证 RAG 检索链路。

`openai` 模式用于真实问答：

- Embedding：`OPENAI_EMBEDDING_MODEL`。
- LLM：`OPENAI_CHAT_MODEL`，通过 Responses API 调用。
- Base URL：可通过 `OPENAI_BASE_URL` 切换到 OpenAI 兼容中转站。

切换 Embedding 模型后需要重建索引，因为不同模型的向量维度可能不同。

`local` Embedding 模式用于中转站没有 Embedding 通道的场景：

- 默认模型：`BAAI/bge-small-zh-v1.5`。
- 向量维度：512。
- 适合中文知识库语义检索。

## 回答模式

严格知识库模式：

- API 值：`strict`。
- 只根据检索片段回答。
- 知识库信息不足时拒答。
- 适合企业制度、论文、代码库等高准确场景。

知识库增强模式：

- API 值：`augmented`。
- 优先使用知识库。
- 知识库不足时允许模型使用通用知识补充。
- 响应中的 `answer_basis` 会标记答案依据。

## 数据边界

以下内容属于运行数据，默认不提交到 Git：

- `data/uploads/`
- `data/chroma/`
- `data/registry.json`
- `.env`
