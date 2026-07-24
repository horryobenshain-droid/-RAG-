# v1.0.0 - 部署与发布版

发布日期：2026-07-24

## 版本定位

`v1.0.0` 将项目从本机工作台升级为可重复部署、可保护入口、可持久化和可运维的 RAG
应用。现有对话、文档与代码库入库、配置中心、评估和 Ollama 能力保持兼容。

## 主要变化

- 一个非 root Python 镜像同时承载 FastAPI 和 Streamlit 运行时。
- Compose 自动启动 Ollama、拉取目标模型，并按健康状态依次启动后端、前端和 Nginx。
- Nginx 使用不进入 Git 的密码文件生成 bcrypt Basic Auth，支持 Streamlit WebSocket 和长请求。
- `rag_data`、`huggingface_cache`、`ollama_data` 三个命名卷分离业务数据与可重建缓存。
- 提供默认 CPU 模式和 NVIDIA GPU Compose 覆盖文件。
- FastAPI CORS 从任意来源调整为可配置白名单；生产默认关闭浏览器跨域访问。
- Windows 与 Linux 启动助手负责生成生产配置、创建密码并启动服务。
- CI 增加 Compose 配置校验，部署文档覆盖 HTTPS、备份、升级和发布。

## 升级说明

从本机版本升级时，Docker 命名卷默认不会自动导入原有 `data/`。需要迁移历史知识库的部署者
应先完整备份原目录，再把内容恢复到 `rag-studio_rag_data`。如果
`data/runtime_config.json` 中的 Ollama 地址仍是 `http://127.0.0.1:11434`，应在配置中心改为
`http://ollama:11434`，或移除该运行时配置后使用生产环境变量。

切换 Embedding 模型、向量维度或 chunk 参数后仍需清空并重新入库。

## 安全边界

- 默认入口只监听宿主机回环地址，公网需要额外的 HTTPS 终止层。
- Basic Auth 密码必须不少于 12 位，且只存放在 `deploy/secrets/auth_password`。
- FastAPI、Streamlit 与 Ollama 均不直接映射端口。
- `.env.production`、密码文件、上传内容、向量库和本地模型不会提交到 Git。

Basic Auth 不是多租户权限系统。需要用户注册、角色、审计或知识库隔离的场景，应在后续版本
增加应用级身份认证与授权。

## 验证基线

- `ruff check .`
- `pytest -q`
- `docker compose --env-file .env.production config --quiet`
- Nginx、Streamlit、FastAPI 与 Ollama 健康检查

完整操作步骤见 [部署文档](deployment.md)。
