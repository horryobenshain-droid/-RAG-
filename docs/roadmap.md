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

## v0.6.0 - RAG 评估与模型对比（已完成）

- 已新增带 schema 校验的 `eval/eval_cases.json`。
- 已支持批量提问，记录答案、命中来源、评分、耗时与单题错误。
- 已输出 `Recall@K`、引用命中率、关键词召回率、通过率、平均与 P95 延迟。
- 已支持通过 profile 对比 OpenAI、Ollama Qwen 和 Ollama Llama。
- 已生成 Markdown 与 JSON 双格式报告，并提供可复现的示例语料。

## v0.7.0 - RAG 质量优化（已完成）

- 已接入可选 CrossEncoder Reranker，并采用懒加载避免默认下载模型。
- 已支持 similarity / MMR 全局配置和单次问答策略切换。
- 已配置化 `top_k`、`fetch_k`、`chunk_size`、`chunk_overlap`、MMR 与混合重排权重。
- 已增强来源诊断，展示各信号分数、初始排名、命中原因和分阶段耗时。
- 已扩展 v0.6.0 评测 profile 与报告，可对比检索和 Reranker 配置。

## v0.8.0 - 代码库批量入库（已完成）

- 已支持 ZIP 上传、安全解压和批量文件解析。
- 已自动忽略 `.git`、`node_modules`、`.venv`、`dist`、二进制文件和构建产物。
- 已保留代码库 ID、目录路径、模块路径和代码符号信息作为来源元数据。
- 已支持按代码库删除源文件与索引，以及分阶段重建索引。
- 已增加代码库问答评测样例。

## v0.9.0 - 产品化 UI 与配置中心（已完成）

- 已支持在 Streamlit 中选择 LLM Provider 和 OpenAI、Qwen、Llama 模型。
- 已展示当前模型状态、Ollama 连通性、Embedding 配置和知识库统计。
- 已增加模型参数、检索参数、切分参数和回答模式的可视化配置。
- 已支持聊天历史导出、来源复制、来源下载和全文展开。
- 已将界面重组为对话工作台、知识库和配置中心。

## v1.0.0 - 部署与发布版（已完成）

- 已增加 Dockerfile、`docker-compose.yml`、CPU/GPU 模式和数据持久化方案。
- 已增加 Nginx Basic Auth，FastAPI、Streamlit 与 Ollama 仅通过容器网络通信。
- 已补充 Nginx、HTTPS、健康检查、备份、升级与回滚文档。
- 已增加部署架构图和 Release notes。
- 已使用 GitHub Actions 自动运行 Ruff、pytest 和 Compose 配置校验。
