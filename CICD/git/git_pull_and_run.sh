#从gitee中pull代码，并重启服务

# !/bin/bash

APP_DIR="/www/wwwroot/python-gitee-test"
PY="/usr/local/python312/bin/python3.12"
BRANCH="main"
LOG="/www/wwwroot/python-gitee-test/deploy.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] webhook start" >> "$LOG"

# 只处理 param=run
if [ "$1" != "run" ]; then
    echo "param not run, skip" >> "$LOG"
    exit 0
fi

cd "$APP_DIR" || exit 1
git config --global --add safe.directory "$APP_DIR"

# 拉最新代码
git fetch --all >> "$LOG" 2>&1
git reset --hard origin/$BRANCH >> "$LOG" 2>&1

# 虚拟环境
source "$APP_DIR/venv/bin/activate"

pip install -r requirements.txt >> "$LOG" 2>&1

# 杀掉旧进程
pkill -f "run.py" 2>/dev/null
sleep 1

# 启动
nohup "$PY" run.py >> "$LOG" 2>&1 &

echo "[$(date '+%Y-%m-%d %H:%M:%S')] run.py restarted" >> "$LOG"