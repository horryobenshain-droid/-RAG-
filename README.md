# 本地 RAG 知识库

一个基于 RAG（检索增强生成）的本地知识库问答系统。项目支持上传 PDF、Word、Markdown、TXT 与常见代码文件，自动完成解析、切分、向量化、持久化检索，并基于检索片段生成带来源引用的回答。

## 当前版本

`v0.2.0` 已完成真实 RAG 管线的核心工程能力：

- 文档上传、解析、切分与 Chroma 向量入库。
- 文档注册表：记录 `document_id`、文件哈希、入库时间、chunk 数、模型配置。
- 知识库管理：查看已入库文档、删除单个文档、清空知识库。
- 问答增强：返回检索来源、相关度分数、耗时、LLM Provider、Embedding Provider。
- 防幻觉 Prompt：要求模型只基于检索片段回答，信息不足时明确说明。
- 简体中文 Streamlit 界面。
- demo / OpenAI 两种 provider 模式。

## 技术栈

- Python 3.11+
- FastAPI
- Streamlit
- LangChain Core / Text Splitters
- Chroma
- OpenAI Responses API / OpenAI Embeddings
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

访问：

- 前端界面：<http://127.0.0.1:8501>
- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

## 模型配置

默认使用 `demo` 模式，不需要 API Key，可以先验证上传、入库、检索、来源展示和知识库管理流程。

要启用 OpenAI，请编辑 `.env`：

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_CHAT_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

如果使用 OpenAI 兼容中转站，可以填写中转站提供的地址：

```env
OPENAI_API_KEY=your_gateway_key
OPENAI_BASE_URL=https://your-gateway.example.com/v1
```

中转站需要同时兼容 Responses API 和 Embeddings API。若只支持 Chat Completions，后续需要再增加一个 `chat_completions` LLM 适配器。

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
- `elapsed_ms`：检索与生成耗时。
- `llm_provider` / `llm_model`：当前回答模型配置。
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
- `v0.3.0`：代码库专用 RAG，支持 zip 上传、路径过滤、函数/类级 chunk。
- `v0.4.0`：接入 Ollama，支持 Qwen / Llama 本地模型。
- `v1.0.0`：评估集、Prompt 版本管理、架构图、演示截图和部署文档。

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
