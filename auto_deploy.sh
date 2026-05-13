#!/bin/bash
# 自动部署脚本 - 由 Gitee Webhook 触发
# 功能：拉取最新代码、重启 Docker 服务、清理旧镜像

PROJECT_DIR="/root/supertech-program-manager"
LOG_FILE="/root/deploy.log"
WEBHOOK_SECRET="supertech2026"

echo "===== 开始部署 $(date) =====" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR" || exit 1

# 拉取最新代码
echo "[1/5] 拉取最新代码..." | tee -a "$LOG_FILE"
git pull origin main >> "$LOG_FILE" 2>&1

# 停止并移除旧容器
echo "[2/5] 停止旧容器..." | tee -a "$LOG_FILE"
docker compose -f "$PROJECT_DIR/docker-compose.yml" down >> "$LOG_FILE" 2>&1

# 清理未使用的镜像（悬空镜像）
echo "[3/5] 清理悬空镜像..." | tee -a "$LOG_FILE"
docker image prune -f >> "$LOG_FILE" 2>&1

# 清理超过24小时的未使用镜像（更彻底的清理）
echo "[4/5] 清理旧镜像..." | tee -a "$LOG_FILE"
docker image prune -a -f --filter "until=24h" >> "$LOG_FILE" 2>&1

# 清理构建缓存
docker builder prune -f >> "$LOG_FILE" 2>&1

# 重新构建并启动
echo "[5/5] 启动新容器..." | tee -a "$LOG_FILE"
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build >> "$LOG_FILE" 2>&1

echo "===== 部署完成 $(date) =====" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
