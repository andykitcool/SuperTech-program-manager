#!/bin/bash
# 自动部署脚本 - 由 Gitee Webhook 触发
# 功能：拉取最新代码、智能部署（纯代码变更只重启，依赖变更才完整重建）
#
# 优化说明：
# - API 的 ./server/app 目录通过 volume 挂载进容器，纯 Python 代码改完只需重启容器
# - 前端代码仍在镜像里，有变更时需要重建 web 容器
# - 只有依赖变更（requirements.txt、Dockerfile 等）才触发完整重建（down + up --build）

PROJECT_DIR="/root/supertech-program-manager"
LOG_FILE="/root/deploy.log"
WEBHOOK_SECRET="supertech2026"

log() {
    echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log "===== 开始部署 ====="
cd "$PROJECT_DIR" || exit 1

# 记录变更前 HEAD，用于对比
OLD_HEAD=$(git rev-parse HEAD)

# 拉取最新代码
log "[1/4] 拉取最新代码..."
git fetch origin main >> "$LOG_FILE" 2>&1
git reset --hard origin/main >> "$LOG_FILE" 2>&1
NEW_HEAD=$(git rev-parse HEAD)

if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
    log "  无新提交，跳过部署"
    exit 0
fi

# 获取变更文件列表
CHANGED_FILES=$(git diff --name-only "$OLD_HEAD".."$NEW_HEAD")
log "  变更文件:"
echo "$CHANGED_FILES" | sed 's/^/    - /' | tee -a "$LOG_FILE"

# 判断各类变更
NEED_API_REBUILD=false    # 需要完整重建 API 镜像
NEED_WEB_REBUILD=false    # 需要完整重建 web 镜像
NEED_API_RESTART=false    # 只需重启 API 容器（代码已通过 volume 同步）

for file in $CHANGED_FILES; do
    case "$file" in
        # API 依赖/配置变更 → 需要完整重建镜像
        server/requirements.txt|server/Dockerfile|server/.dockerignore|server/entrypoint.sh)
            NEED_API_REBUILD=true
            ;;
        # API Python 代码变更 → 只需重启（volume 挂载了代码目录）
        server/app/*|server/scripts/*|server/migrations/*)
            NEED_API_RESTART=true
            ;;
        # web 依赖/配置变更 → 需要完整重建镜像
        web/package*.json|web/Dockerfile|web/nginx.conf|web/index.html)
            NEED_WEB_REBUILD=true
            ;;
        # web 源码变更 → 需要重建前端镜像（前端代码在镜像里，无 volume 挂载）
        web/src/*|web/public/*)
            NEED_WEB_REBUILD=true
            ;;
        # docker-compose 变更 → 所有容器都需要重建
        docker-compose.yml)
            NEED_API_REBUILD=true
            NEED_WEB_REBUILD=true
            ;;
    esac
done

# ---- 执行部署 ----

# 情况 A：API 依赖变更 → 需要 full rebuild
if [ "$NEED_API_REBUILD" = true ]; then
    log "[2/4] API 依赖有变更，完整重建..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" down >> "$LOG_FILE" 2>&1
    docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build >> "$LOG_FILE" 2>&1
else
    # 情况 B：只需重建 web 和/或重启 API

    # web 有变更 → 只重建 web 容器
    if [ "$NEED_WEB_REBUILD" = true ]; then
        log "[2/4] 前端有变更，重建 web 容器..."
        docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build --no-deps web >> "$LOG_FILE" 2>&1
    fi

    # API 代码有变更 → 只重启 API 容器（代码已通过 volume 同步）
    if [ "$NEED_API_RESTART" = true ]; then
        log "[3/4] API 代码有变更，重启 api 容器..."
        docker compose -f "$PROJECT_DIR/docker-compose.yml" restart api >> "$LOG_FILE" 2>&1
    fi

    # 都没有发生变更（比如只改了文档）→ 无需操作
    if [ "$NEED_WEB_REBUILD" = false ] && [ "$NEED_API_RESTART" = false ]; then
        log "[2/4] 仅文档/配置变更，无需重启服务"
    fi
fi

# 清理悬空镜像（不影响构建缓存）
log "清理悬空镜像..."
docker image prune -f >> "$LOG_FILE" 2>&1

log "===== 部署完成 ====="
echo "" | tee -a "$LOG_FILE"
