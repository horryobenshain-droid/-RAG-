# Local RAG Knowledge Base

基于 RAG（Retrieval-Augmented Generation，检索增强生成）的本地知识库问答系统。项目支持上传 PDF、Word、Markdown、TXT 与常见代码文件，自动解析、切分、向量化并写入本地向量数据库，然后根据检索结果生成带来源引用的回答。

## 项目亮点

- 本地文档解析：支持 PDF、Word、Markdown、TXT 和常见代码文件。
- RAG 闭环：覆盖文档加载、文本切分、Embedding、向量检索、Prompt 组装和答案生成。
- 本地向量库：使用 Chroma 持久化存储，适合个人知识库与简历演示。
- 模型可切换：默认 demo 模式可无密钥运行，也可切换到 OpenAI 模型。
- 来源追踪：回答返回命中文档、页码、chunk 编号和片段预览。
- 前后端分离：FastAPI 提供接口，Streamlit 提供轻量可视化界面。

## 技术栈

- Python 3.11+
- FastAPI
- Streamlit
- LangChain
- Chroma
- OpenAI / 本地模型扩展预留

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

默认配置使用 `demo` 模式，不需要 API Key，可以先验证上传、入库、检索和来源展示流程。要使用 OpenAI，请在 `.env` 中设置：

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
```

切换 Embedding 模型或 Provider 后，建议清空 `data/chroma/` 重新入库，避免向量维度不一致。

## API

后端启动后可访问：

- `GET /health`：健康检查
- `POST /api/upload`：上传并入库文档
- `POST /api/chat`：基于知识库问答

示例请求：

```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{"question":"这份文档主要讲了什么？","top_k":4}'
```

## 目录结构

```text
.
├─ app/
│  ├─ api/              # FastAPI 路由与请求响应模型
│  ├─ core/             # 配置、文件工具
│  ├─ loaders/          # 本地文档加载器
│  ├─ rag/              # Embedding、切分、向量库、问答链
│  └─ main.py           # FastAPI 应用入口
├─ data/
│  ├─ uploads/          # 用户上传文件，默认不提交
│  └─ chroma/           # Chroma 持久化数据，默认不提交
├─ docs/
│  ├─ architecture.md   # 架构说明
│  └─ roadmap.md        # 迭代路线
├─ tests/
├─ ui/
│  └─ streamlit_app.py  # Streamlit 前端
├─ .env.example
├─ pyproject.toml
└─ requirements.txt
```

## 版本规划

- `v0.1.0`：项目骨架、上传接口、基础 RAG 闭环、Streamlit 页面。
- `v0.2.0`：多知识库管理、删除/重建索引、检索参数配置。
- `v0.3.0`：代码库专用解析策略，按函数、类、路径增强检索。
- `v0.4.0`：接入 Ollama，支持 Qwen / Llama 本地模型。
- `v1.0.0`：加入评估集、耗时统计、Prompt 版本管理和完整演示文档。

## Git 工作流

建议按功能分支迭代：

```powershell
git checkout -b feature/knowledge-base-management
git add .
git commit -m "feat: add knowledge base management"
git push origin feature/knowledge-base-management
```

稳定版本可以打 tag：

```powershell
git tag v0.1.0
git push origin v0.1.0
```
