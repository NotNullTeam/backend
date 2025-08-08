# Backend Dockerfile for IP Expert project
# Multi-stage not required (small project). Use slim image for minimal size.

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 使用更可靠的方法配置apt源 - 创建新的源文件而不是修改现有文件
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

# 创建pip配置使用国内镜像源
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple/" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf

# 安装基础必备依赖（将大型依赖分开安装，提高成功率）
COPY requirements.txt ./

# 分步安装依赖，先安装一些基础依赖
RUN pip install --no-cache-dir wheel setuptools

# 安装基本的web和数据库依赖
RUN pip install --no-cache-dir Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Flask-Migrate==4.0.5 \
    Flask-JWT-Extended==4.5.2 Flask-CORS==4.0.0 Flask-WTF==1.1.1 \
    python-dotenv==1.0.0 requests==2.31.0

# 安装数据处理依赖
RUN pip install --no-cache-dir pandas==2.3.1 numpy==2.3.2

# 安装其他剩余依赖，排除torch（最后单独安装）
RUN pip install --no-cache-dir $(grep -v "torch" requirements.txt | grep -v "^#" | grep -v "^$") && \
    pip cache purge

# 单独安装torch，使用清华源加速下载
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple/ torch>=2.0.0 && \
    pip cache purge

# Copy project source
COPY . .

# Expose Flask port
EXPOSE 5001

# Default command (can be overridden by docker-compose)
CMD ["python", "run.py"]
