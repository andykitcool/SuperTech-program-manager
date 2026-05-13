#!/bin/bash
# 自动部署脚本 - 由 Gitee Webhook 触发
# 功能：拉取最新代码、重启 Docker 服务、清理旧镜像
# 注意：保留 Docker 构建缓存以加速小改动部署

PROJECT_DIR="/root/supertech-program-manager"
LOG_FILE="/root/deploy.log"
WEBHOOK_SECRET="supertech2026"

echo "===== 开始部署 $(date) =====" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR" || exit 1

# 拉取最新代码
echo "[1/4] 拉取最新代码..." | tee -a "$LOG_FILE"
git pull origin main >> "$LOG_FILE" 2>&1

# 停止并移除旧容器
echo "[2/4] 停止旧容器..." | tee -a "$LOG_FILE"
docker compose -f "$PROJECT_DIR/docker-compose.yml" down >> "$LOG_FILE" 2>&1

# 清理悬空镜像（不影响构建缓存）
echo "[3/4] 清理悬空镜像..." | tee -a "$LOG_FILE"
docker image prune -f >> "$LOG_FILE" 2>&1

# 重新构建并启动（利用 Docker 层缓存加速构建）
echo "[4/4] 启动新容器..." | tee -a "$LOG_FILE"
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build >> "$LOG_FILE" 2>&1

echo "===== 部署完成 $(date) =====" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
