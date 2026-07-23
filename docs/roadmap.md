# 迭代路线

## v0.1.0 - MVP 骨架

- FastAPI 后端。
- Streamlit 前端。
- 本地文档上传。
- 文档加载、切分、向量化和 Chroma 持久化。
- demo / OpenAI provider 预留。
- 来源片段返回。

## v0.2.0 - 真实 RAG 管线与知识库管理

- 文档注册表：记录文档 ID、文件哈希、入库时间、chunk 数和模型配置。
- 知识库管理：查看已入库文档、删除单个文档、清空知识库。
- 检索增强：返回相关度分数、召回数量和耗时。
- Prompt 增强：要求模型只基于检索片段回答，信息不足时拒答。
- Streamlit 简体中文界面。
- API smoke tests 覆盖上传、问答、列表、删除和清空。

## v0.3.0 - 回答模式与本地 Embedding

- 严格知识库模式：只根据上传文档回答。
- 知识库增强模式：知识库优先，不足时允许模型通用知识补充。
- 响应返回 `answer_mode` 和 `answer_basis`。
- 接入 `sentence-transformers` 与 `BAAI/bge-small-zh-v1.5`。
- 支持“中转站 GPT-5.5 + 本地中文 Embedding”的组合。

## v0.4.0 - 代码感知检索

- 代码专用 chunk 策略：按函数、类和行号组织。
- 来源展示语言、函数名和行号范围。
- 混合检索：向量分 + 关键词分 + 文件名/函数名加权。
- 来源诊断展示综合分、向量分、关键词分和命中词。
- 算法模板 Prompt 优化。

## v0.5.0 - 本地模型支持

- Ollama provider adapter。
- Qwen / Llama 模型预设。
- Ollama base URL、模型名、temperature、context length、timeout 可配置。
- 支持“本地 LLM + 本地 Embedding”的离线知识库问答组合。

## v0.6.0 - RAG 评估与模型对比

- 新增评估数据集，例如 `eval_cases.json`。
- 支持批量提问评估，记录每个问题的命中来源、回答内容和耗时。
- 输出 `Recall@K`、平均延迟、引用命中情况等指标。
- 对比 `OpenAI`、`Ollama Qwen`、`Ollama Llama` 在同一知识库上的效果。
- 生成 `eval_report.md`，用于沉淀评估结果和调参结论。

## v0.7.0 - RAG 质量优化

- Reranker 接入。
- MMR / similarity 检索策略切换。
- `top_k`、`fetch_k`、`chunk_size`、`chunk_overlap` 等参数配置化。
- 增强检索诊断，展示每个来源被命中的原因。
- 基于 v0.6.0 评估结果优化 chunk 策略、重排权重和 Prompt。

## v0.8.0 - 代码库批量入库

- 支持 zip 上传和批量文件解析。
- 自动忽略 `.git`、`node_modules`、`.venv`、`dist`、二进制文件和构建产物。
- 保留目录路径、模块路径和代码符号信息作为来源元数据。
- 支持按代码库删除、重建索引。
- 增加代码库问答评测样例。

## v0.9.0 - 产品化 UI 与配置中心

- 在 Streamlit 中选择 LLM Provider 和模型，例如 OpenAI、Qwen、Llama。
- 展示当前模型状态、Ollama 连通性、Embedding 配置和知识库统计。
- 增加模型参数、检索参数和回答模式的可视化配置。
- 支持聊天历史导出、来源复制、来源全文展开。
- 优化界面信息架构，使其更接近可演示的知识库工作台。

## v1.0.0 - 部署与发布版

- Dockerfile、`docker-compose.yml` 和数据目录持久化方案。
- 基础鉴权，避免公网部署时直接暴露上传和问答接口。
- Nginx / 云服务器部署文档。
- 架构图、演示截图和部署文档。
- Release notes 和完整项目复盘。
- GitHub Actions 自动运行 `ruff` 和 `pytest`。
