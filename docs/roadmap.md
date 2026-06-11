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

## v0.3.0 - 代码库 RAG

- 支持 zip 上传和批量文件解析。
- 忽略二进制、依赖目录和构建产物。
- 代码专用 chunk 策略：按路径、类、函数组织。
- 来源展示文件路径和行号范围。
- 增加代码问答测试集。

## v0.4.0 - 本地模型支持

- Ollama provider adapter。
- Qwen / Llama 模型预设。
- 本地 embedding 模型选项。
- OpenAI 与本地模型效果对比文档。

## v0.5.0 - RAG 质量优化

- Reranker 接入。
- MMR / similarity 检索策略切换。
- Chunk size、overlap、top-k 可配置。
- Prompt 模板版本管理。

## v1.0.0 - 简历展示版

- 评估数据集。
- 召回率、回答准确率、耗时统计。
- 架构图、演示截图和部署文档。
- Release notes 和完整项目复盘。
