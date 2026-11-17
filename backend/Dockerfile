# ===== 后端镜像：FastAPI + LangGraph + MCP（uv 构建）=====

# ---------- 阶段一：构建依赖 ----------
FROM ghcr.io/astral-sh/uv:0.5.11 AS builder

# 让 uv 使用国内镜像源，加速依赖下载
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# 先只拷贝依赖声明文件，利用 Docker 层缓存：
# 依赖不变时，重新构建不会重复下载安装
COPY pyproject.toml uv.lock ./

# 用 uv sync 安装依赖到 /app/.venv
# --frozen 严格按 uv.lock 锁定版本；--no-dev 不装 dev 依赖（pytest/ruff 等）
RUN uv sync --frozen --no-dev --no-install-project

# ---------- 阶段二：运行镜像 ----------
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制已装好的虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制应用源码
COPY app ./app

# 让 Python 使用虚拟环境里的解释器和包
ENV PATH="/app/.venv/bin:$PATH"

# 暴露服务端口（config.py 默认 8000）
EXPOSE 8000

# 启动命令：uvicorn 启动 FastAPI
# --host 0.0.0.0 让容器外部可访问
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
