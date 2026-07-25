# 本地 RAG 知识库

一个基于 RAG（检索增强生成）的本地知识库问答系统。项目支持上传 PDF、Word、Markdown、TXT 与常见代码文件，自动完成解析、切分、向量化、持久化检索，并基于检索片段生成带来源引用的回答。

## 当前版本

`v1.0.0` 已将知识库工作台补齐为可容器化部署和发布的完整版本：

- 生产部署：使用 Docker Compose 编排 Nginx、Streamlit、FastAPI 与 Ollama。
- 入口保护：Nginx Basic Auth、私有服务网络、显式 CORS 白名单和安全响应头。
- 数据持久化：应用数据、HuggingFace 缓存与 Ollama 模型使用独立命名卷。
- 可运维性：健康检查、自动重启、CPU/GPU 模式、备份、升级与回滚说明。
- 发布质量：GitHub Actions 自动执行 Ruff、pytest 和 Compose 配置校验。

- 三视图工作台：对话、知识库和配置中心各自承载独立任务。
- 运行时配置：在界面中切换 demo、OpenAI、Ollama Qwen / Llama 和 Embedding。
- 配置持久化：模型、生成、检索、切分和 Reranker 参数经校验后写入本地配置。
- 服务状态：展示当前模型、Ollama 连通性、本地模型列表和知识库统计。
- 对话资产：支持 Markdown 导出、来源全文展开、复制和单独下载。
- 索引保护：Embedding 配置与现有索引不一致时显示重建提示。
- 文档上传、解析、切分与 Chroma 向量入库。
- 文档注册表：记录 `document_id`、文件哈希、入库时间、chunk 数、模型配置。
- 知识库管理：查看已入库文档、删除单个文档、清空知识库。
- 问答增强：返回检索来源、相关度分数、耗时、LLM Provider、Embedding Provider。
- 防幻觉 Prompt：要求模型只基于检索片段回答，信息不足时明确说明。
- 回答模式：支持“严格知识库”和“知识库增强”两种策略。
- 本地 Embedding：支持 `BAAI/bge-small-zh-v1.5`，适合中文语义检索。
- 代码感知切分：对代码文件记录语言、函数名、起止行号。
- 代码库批量入库：上传 ZIP 后自动扫描、过滤并批量建立索引。
- 路径元数据：保留代码库、相对路径、模块路径、代码符号与行号。
- 代码库管理：支持按代码库查看、删除源文件与索引，以及原位重建索引。
- 安全过滤：拒绝路径穿越，限制文件数量与大小，忽略依赖、构建产物和二进制文件。
- 混合检索：结合向量分、关键词命中、文件名和函数名命中重排结果。
- 检索策略：支持 similarity 与 MMR，并可在每次问答时切换。
- 可选 Reranker：通过 CrossEncoder 对初召回候选执行二次语义重排。
- 检索诊断：展示完整分数组成、初始排名、命中原因、候选数和分阶段耗时。
- 检索参数：`top_k`、`fetch_k`、chunk 参数、MMR 和混合权重均可配置。
- 评估数据集：用 JSON 定义问题、期望来源、答案关键词、禁用词和引用要求。
- 批量模型对比：在同一知识库上比较 OpenAI、Ollama Qwen 和 Ollama Llama。
- 评估指标：输出 Recall@K、引用命中率、关键词召回率、通过率和延迟。
- 评估报告：同时生成 Markdown 审阅报告和 JSON 结构化结果。
- 简体中文 Streamlit 产品化工作台。
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
- Sentence Transformers CrossEncoder Reranker
- PyPDF / docx2txt
- Docker Compose / Nginx

## 快速开始

首次使用界面前，建议先阅读[知识库使用说明](docs/user-guide.md)。

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

生产容器部署：

```powershell
.\deploy\start.ps1 start
```

默认入口为 [http://127.0.0.1:8080](http://127.0.0.1:8080)，首次启动会要求创建访问密码，
并自动拉取 `.env.production` 中配置的 Ollama 模型。完整的 HTTPS、GPU、备份与升级说明见
[部署文档](docs/deployment.md)。

## 模型配置

默认使用 `demo` 模式，不需要 API Key，可以先验证上传、入库、检索、来源展示和知识库管理流程。

启动服务后可直接在“配置中心”修改模型和检索设置。保存后的运行时配置位于
`data/runtime_config.json`，优先级高于 `.env`，且不会提交到 Git。OpenAI API Key 可写入该本地文件，
但配置查询接口只返回是否已配置，不会回显密钥。修改 Embedding 或 chunk 参数后应清空并重新入库。

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
OLLAMA_NUM_PREDICT=512
OLLAMA_TOP_P=0.9
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_TIMEOUT_SECONDS=120
LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

如需切换到 Llama，将 `OLLAMA_CHAT_MODEL` 改为已拉取的模型名，例如 `llama3.1:8b`。Ollama 只负责生成回答，向量检索仍建议使用 `EMBEDDING_PROVIDER=local`。

切换 Embedding Provider 或 Embedding 模型后，建议在界面中清空知识库并重新入库，避免向量维度不一致。

## 检索与 Reranker 配置

默认使用 similarity 与混合重排，不会额外下载 Reranker 模型：

```env
RETRIEVAL_STRATEGY=similarity
RETRIEVAL_FETCH_K=40
MMR_LAMBDA_MULT=0.5

HYBRID_VECTOR_WEIGHT=0.45
HYBRID_KEYWORD_WEIGHT=0.40
HYBRID_FILENAME_WEIGHT=0.10
HYBRID_SYMBOL_WEIGHT=0.05

RERANKER_PROVIDER=none
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_DEVICE=cpu
RERANKER_CANDIDATE_K=12
RERANKER_BATCH_SIZE=16
RERANKER_WEIGHT=0.60
```

启用二次重排时，将 `RERANKER_PROVIDER` 改为 `cross_encoder`。首次问答会下载
`RERANKER_MODEL`，离线环境应提前准备模型缓存。MMR 的 `MMR_LAMBDA_MULT` 越接近 1
越偏向相关性，越接近 0 越偏向结果多样性。

`CHUNK_SIZE` 或 `CHUNK_OVERLAP` 修改后必须清空知识库并重新入库；四个
`HYBRID_*_WEIGHT` 之和必须为 1。

## 代码库批量入库

在前端选择 `.zip` 文件即可按代码库入库。压缩包可以包含一个公共根目录；入库时会自动
去掉该目录，并保留其余相对路径。`.git`、`node_modules`、`.venv`、`dist`、`build`、
`target`、缓存目录、不支持的文件类型和二进制文件会被忽略。

默认安全限制如下，可在 `.env` 中调整：

```env
REPOSITORY_MAX_ARCHIVE_BYTES=26214400
REPOSITORY_MAX_FILES=2000
REPOSITORY_MAX_FILE_BYTES=2097152
REPOSITORY_MAX_TOTAL_BYTES=52428800
API_INGEST_TIMEOUT_SECONDS=600
```

代码库重建使用已安全解压的源文件。新向量全部写入成功后才会替换旧索引；删除代码库会
同时删除其文档注册记录、向量和持久化源文件。

## RAG 评估

仓库提供一个可复现的小型评估集和四份示例语料。以下命令会先入库尚未存在的示例文件，
再使用当前 `.env` 中的模型运行评估：

```powershell
python -m app.evaluation.cli `
  --dataset eval/eval_cases.json `
  --ingest eval/corpus
```

默认生成：

- `eval/eval_report.md`：模型对比、逐题指标、来源和完整答案。
- `eval/eval_results.json`：适合脚本分析或持续集成的结构化结果。

重复执行 `--ingest` 时会根据文件 SHA256 跳过已入库语料。评估现有知识库时可以省略
`--ingest`，并把 `eval/eval_cases.json` 中的期望来源改成自己的文件名、chunk、文档 ID
或代码符号。

多模型对比使用 profile 文件。先复制示例并只保留本机可用的模型：

```powershell
Copy-Item eval/model_profiles.example.json eval/model_profiles.json

python -m app.evaluation.cli `
  --dataset eval/eval_cases.json `
  --profiles eval/model_profiles.json `
  --top-k 4
```

Profile 允许切换 LLM、检索策略、混合权重和 Reranker 参数，不能写 API Key 或修改 Embedding。
OpenAI Key 继续从 `.env` 读取；Ollama profile 对应的模型需要提前执行 `ollama pull`。
某个模型不可用时，该模型的用例会记录为 `error`，其他模型仍会继续评估。

评估指标定义：

- `Recall@K`：期望来源中出现在前 K 个检索结果里的比例，再对用例取宏平均。
- `引用命中率`：要求引用的用例中，答案是否引用了命中的期望来源。
- `答案关键词召回率`：期望关键词中实际出现在答案里的比例。
- `通过率`：来源、引用、关键词和禁用词检查全部满足的用例比例。
- `平均延迟 / P95 延迟`：成功执行问答用例的端到端耗时。

需要让评估失败反映到命令退出码时，增加 `--fail-on-failure`。

## API

- `GET /health`：健康检查，包含当前版本、模型与默认检索配置。
- `POST /api/upload`：上传并入库文档。
- `POST /api/repositories/upload`：上传 ZIP 并批量入库代码库。
- `GET /api/repositories`：查看已入库代码库。
- `POST /api/repositories/{repository_id}/reindex`：重建指定代码库索引。
- `DELETE /api/repositories/{repository_id}`：删除指定代码库、源文件和索引。
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
- `sources[].filename_score` / `sources[].symbol_score`：文件名和代码符号命中分。
- `sources[].reranker_score`：启用 CrossEncoder 后的二次重排分。
- `sources[].retrieval_rank` / `sources[].reasons`：初始排名和可读命中原因。
- `sources[].matched_keywords`：命中的关键词。
- `sources[].symbol_name` / `start_line` / `end_line`：代码片段定位信息。
- `sources[].repository_id` / `repository_name`：代码库标识与名称。
- `sources[].relative_path` / `module_path`：代码文件相对路径与模块路径。
- `answer_mode`：回答模式，`strict` 或 `augmented`。
- `answer_basis`：答案依据，`knowledge_base`、`model_prior` 或 `mixed`。
- `elapsed_ms`：检索与生成耗时。
- `retrieval_ms` / `reranking_ms` / `generation_ms`：各阶段耗时。
- `retrieval_strategy` / `candidate_count`：本次检索策略和候选数量。
- `reranker_provider` / `reranker_model`：本次二次重排配置。
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
│  ├─ evaluation/       # 评估模型、运行器、报告和 CLI
│  └─ main.py           # FastAPI 应用入口
├─ data/
│  ├─ uploads/          # 用户上传文件，默认不提交
│  ├─ repositories/     # 安全解压后的代码库源文件，默认不提交
│  ├─ chroma/           # Chroma 持久化数据，默认不提交
│  ├─ registry.json     # 文档注册表，默认不提交
│  ├─ repositories.json # 代码库注册表，默认不提交
│  └─ runtime_config.json # 运行时配置，默认不提交
├─ docs/
│  ├─ architecture.md
│  └─ roadmap.md
├─ eval/
│  ├─ corpus/           # 可复现的示例评估语料
│  ├─ eval_cases.json
│  └─ model_profiles.example.json
├─ tests/
├─ ui/
│  └─ streamlit_app.py
├─ deploy/
│  ├─ nginx/           # Nginx 入口、WebSocket 代理与 Basic Auth
│  ├─ secrets/         # 本地部署密码目录，内容不提交
│  ├─ start.ps1        # Windows Compose 部署助手
│  └─ start.sh         # Linux Compose 部署助手
├─ Dockerfile
├─ docker-compose.yml
├─ docker-compose.gpu.yml
├─ .env.example
├─ .env.production.example
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
- `v0.6.0`：评估数据集、批量模型对比、质量指标和 Markdown/JSON 报告。
- `v0.7.0`：MMR / similarity、CrossEncoder Reranker、参数化检索和来源诊断。
- `v0.8.0`：ZIP 代码库批量入库、路径元数据、过滤规则和代码库级索引管理。
- `v0.9.0`：产品化工作台、运行时配置中心、模型状态和对话导出。
- `v1.0.0`：Docker Compose、Nginx 鉴权、持久化、健康检查和发布流程。

当前版本已经形成从本地 RAG、质量评估、产品化配置到受保护部署的完整闭环。

### v0.7.0 - 检索质量优化（已完成）

- 已接入可选 CrossEncoder Reranker，对初召回结果进行二次重排。
- 已增加 MMR / similarity 全局与单次问答策略切换。
- 已配置化 `top_k`、`fetch_k`、chunk、MMR 和重排权重。
- 已增强检索诊断与评测 profile，可直接比较不同检索组合。

### v0.8.0 - 代码库批量入库（已完成）

- 已支持 ZIP 上传、安全解压和批量文件解析。
- 已自动忽略 `.git`、`node_modules`、`.venv`、`dist`、二进制文件和构建产物。
- 已保留代码库 ID、目录路径、模块路径和代码符号信息作为来源元数据。
- 已支持按代码库删除源文件与索引，以及分阶段重建索引。
- 已增加代码库问答评测样例。

### v0.9.0 - 产品化 UI 与配置中心（已完成）

- 已支持在 Streamlit 中选择 LLM Provider 和 OpenAI、Qwen、Llama 模型。
- 已展示当前模型状态、Ollama 连通性、Embedding 配置和知识库统计。
- 已增加模型参数、检索参数、切分参数和回答模式的可视化配置。
- 已支持聊天历史导出、来源复制、来源下载和全文展开。
- 已将界面重组为对话工作台、知识库和配置中心。

### v1.0.0 - 部署与发布版（已完成）

- 已增加 Dockerfile、`docker-compose.yml` 和三个独立持久卷。
- 已使用 Nginx Basic Auth 保护唯一公开入口，FastAPI 与 Ollama 不映射宿主机端口。
- 已补充 Nginx、HTTPS、GPU、备份、升级和发布文档。
- 已增加部署架构图与 `v1.0.0` Release notes。
- 已使用 GitHub Actions 自动运行 Ruff、pytest 和 Compose 配置校验。

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
git tag v1.0.0
git push origin v1.0.0
```
