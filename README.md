# 本地 RAG 知识库

一个基于 RAG（检索增强生成）的本地知识库问答系统。项目支持上传 PDF、Word、Markdown、TXT 与常见代码文件，自动完成解析、切分、向量化、持久化检索，并基于检索片段生成带来源引用的回答。

## 当前版本

`v0.5.0` 已接入 Ollama，可使用 Qwen / Llama 本地模型完成知识库问答：

- 文档上传、解析、切分与 Chroma 向量入库。
- 文档注册表：记录 `document_id`、文件哈希、入库时间、chunk 数、模型配置。
- 知识库管理：查看已入库文档、删除单个文档、清空知识库。
- 问答增强：返回检索来源、相关度分数、耗时、LLM Provider、Embedding Provider。
- 防幻觉 Prompt：要求模型只基于检索片段回答，信息不足时明确说明。
- 回答模式：支持“严格知识库”和“知识库增强”两种策略。
- 本地 Embedding：支持 `BAAI/bge-small-zh-v1.5`，适合中文语义检索。
- 代码感知切分：对代码文件记录语言、函数名、起止行号。
- 混合检索：结合向量分、关键词命中、文件名和函数名命中重排结果。
- 检索诊断：来源片段展示综合分、向量分、关键词分和命中词。
- 简体中文 Streamlit 界面。
- demo / OpenAI / Ollama 三种 LLM provider 模式。

## 技术栈

- Python 3.11+
- FastAPI
- Streamlit
- LangChain Core / Text Splitters
- Chroma
- OpenAI Responses API / OpenAI Embeddings
- Ollama 本地 Chat API
- Sentence Transformers / HuggingFace Embeddings
- PyPDF / docx2txt

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

启动后端：

```powershell
uvicorn app.main:app --reload --port 8000
```

启动前端：

```powershell
streamlit run ui/streamlit_app.py
```

Windows 一键启动：

```powershell
.\start.ps1
```

访问：

- 前端界面：[http://127.0.0.1:8501](http://127.0.0.1:8501)
- API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## 模型配置

默认使用 `demo` 模式，不需要 API Key，可以先验证上传、入库、检索、来源展示和知识库管理流程。

要启用 OpenAI，请编辑 `.env`：

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=local
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_CHAT_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

如果使用 OpenAI 兼容中转站，可以填写中转站提供的地址：

```env
OPENAI_API_KEY=your_gateway_key
OPENAI_BASE_URL=https://your-gateway.example.com/v1
```

中转站需要同时兼容 Responses API 和 Embeddings API。若只支持 Chat Completions，后续需要再增加一个 `chat_completions` LLM 适配器。
如果中转站没有 Embedding 通道，推荐保持：

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=local
```

这样可以使用中转站 GPT-5.5 生成答案，同时用本地中文 Embedding 做向量检索。

要启用 Ollama 本地模型，请先启动 Ollama 并拉取模型：

```powershell
ollama pull qwen2.5:7b
# 或者
ollama pull llama3.1:8b
```

然后编辑 `.env`：

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_TEMPERATURE=0.2
OLLAMA_NUM_CTX=8192
OLLAMA_TIMEOUT_SECONDS=120
LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

如需切换到 Llama，将 `OLLAMA_CHAT_MODEL` 改为已拉取的模型名，例如 `llama3.1:8b`。Ollama 只负责生成回答，向量检索仍建议使用 `EMBEDDING_PROVIDER=local`。

切换 Embedding Provider 或 Embedding 模型后，建议在界面中清空知识库并重新入库，避免向量维度不一致。

## API

- `GET /health`：健康检查。
- `POST /api/upload`：上传并入库文档。
- `POST /api/chat`：基于知识库问答。
- `GET /api/documents`：查看已入库文档。
- `DELETE /api/documents/{document_id}`：删除单个文档及其向量。
- `DELETE /api/documents`：清空知识库。

问答示例：

```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{"question":"这份文档主要讲了什么？","top_k":4}'
```

响应会包含：

- `answer`：回答内容。
- `sources`：来源文件、页码、chunk、相关度分数和片段预览。
- `sources[].vector_score`：原始向量相关度。
- `sources[].keyword_score`：关键词命中分。
- `sources[].matched_keywords`：命中的关键词。
- `sources[].symbol_name` / `start_line` / `end_line`：代码片段定位信息。
- `answer_mode`：回答模式，`strict` 或 `augmented`。
- `answer_basis`：答案依据，`knowledge_base`、`model_prior` 或 `mixed`。
- `elapsed_ms`：检索与生成耗时。
- `llm_provider` / `llm_model`：当前回答模型配置，支持 `demo`、`openai`、`ollama`。
- `embedding_provider` / `embedding_model`：当前向量模型配置。

## 目录结构

```text
.
├─ app/
│  ├─ api/              # FastAPI 路由与 Pydantic 模型
│  ├─ core/             # 配置、文件工具、文档注册表
│  ├─ loaders/          # PDF、Word、文本、代码文件加载
│  ├─ rag/              # Embedding、切分、向量库、Prompt、问答服务
│  └─ main.py           # FastAPI 应用入口
├─ data/
│  ├─ uploads/          # 用户上传文件，默认不提交
│  ├─ chroma/           # Chroma 持久化数据，默认不提交
│  └─ registry.json     # 文档注册表，默认不提交
├─ docs/
│  ├─ architecture.md
│  └─ roadmap.md
├─ tests/
├─ ui/
│  └─ streamlit_app.py
├─ .env.example
├─ pyproject.toml
└─ requirements.txt
```

## 开发验证

```powershell
ruff check .
pytest -q
```

## 版本规划

- `v0.1.0`：项目骨架、上传接口、基础 RAG 闭环、Streamlit 页面。
- `v0.2.0`：文档注册表、知识库管理、检索分数、耗时统计、中文界面。
- `v0.3.0`：回答模式、本地中文 Embedding、答案依据标记。
- `v0.4.0`：代码感知切分、混合检索、来源诊断。
- `v0.5.0`：接入 Ollama，支持 Qwen / Llama 本地模型。

后续目标是把项目从“可运行的 RAG demo”升级为“可评估、可部署、可配置、可信任的专业知识库应用”。

### v0.6.0 - RAG 评估与模型对比

- 新增评估数据集，例如 `eval_cases.json`。
- 支持批量提问评估，记录每个问题的命中来源、回答内容和耗时。
- 输出 `Recall@K`、平均延迟、引用命中情况等指标。
- 对比 `OpenAI`、`Ollama Qwen`、`Ollama Llama` 在同一知识库上的效果。
- 生成 `eval_report.md`，用于沉淀评估结果和调参结论。

### v0.7.0 - 检索质量优化

- 接入 reranker，对初召回结果进行二次重排。
- 增加 MMR / similarity 检索策略切换。
- 将 `top_k`、`fetch_k`、`chunk_size`、`chunk_overlap` 等参数配置化。
- 增强检索诊断，展示每个来源被命中的原因。
- 基于 v0.6.0 评估结果优化 chunk 策略、重排权重和 Prompt。

### v0.8.0 - 代码库批量入库

- 支持 zip 上传和批量文件解析。
- 自动忽略 `.git`、`node_modules`、`.venv`、`dist`、二进制文件和构建产物。
- 保留目录路径、模块路径和代码符号信息作为来源元数据。
- 支持按代码库删除、重建索引。
- 增加代码库问答评测样例。

### v0.9.0 - 产品化 UI 与配置中心

- 在 Streamlit 中选择 LLM Provider 和模型，例如 OpenAI、Qwen、Llama。
- 展示当前模型状态、Ollama 连通性、Embedding 配置和知识库统计。
- 增加模型参数、检索参数和回答模式的可视化配置。
- 支持聊天历史导出、来源复制、来源全文展开。
- 优化界面信息架构，使其更接近可演示的知识库工作台。

### v1.0.0 - 部署与发布版

- 增加 Dockerfile、`docker-compose.yml` 和数据目录持久化方案。
- 增加基础鉴权，避免公网部署时直接暴露上传和问答接口。
- 补充 Nginx / 云服务器部署文档。
- 增加架构图、演示截图、Release notes 和完整项目复盘。
- 使用 GitHub Actions 自动运行 `ruff` 和 `pytest`。

## Git 工作流

建议按功能分支迭代：

```powershell
git checkout -b feature/code-repository-rag
git add .
git commit -m "feat: add code repository ingestion"
git push origin feature/code-repository-rag
```

稳定版本可以打 tag：

```powershell
git tag v0.2.0
git push origin v0.2.0
```
