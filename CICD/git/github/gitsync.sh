#!/bin/bash

###################
# gitee 手工提交
# /D/workspace_python/infinity/CICD/git/github/gitsync.sh
###################

echo "----Started----"

echo "----clone https://gitee.com/snetlogon20/infinity----"
mkdir -p /D/workspace_python/giteeRepo/
cd /D/workspace_python/giteeRepo/
rm -rf /D/workspace_python/giteeRepo/infinity/
git clone https://gitee.com/snetlogon20/infinity

#cd /D/workspace_python/giteeRepo/infinity/Infinity/
#git pull origin main

echo "----cp to githubRepo----"
mkdir -p /D/workspace_python/githubRepo/Infinity/
cd /D/workspace_python/githubRepo/Infinity/
rm -rf /D/workspace_python/githubRepo/Infinity/CICD
rm -rf /D/workspace_python/githubRepo/Infinity/dataIntegrator
cp -r /D/workspace_python/giteeRepo/infinity/CICD /D/workspace_python/githubRepo/Infinity
cp -r /D/workspace_python/giteeRepo/infinity/dataIntegrator /D/workspace_python/githubRepo/Infinity

cd /D/workspace_python/githubRepo/Infinity/

echo "----Checking Git status----"
git status
git add .
git status
git commit -m "repo sync"

echo "----Start pushing to GitHub----"
git remote set-url origin https://github.com/snetlogon20/Infinity.git
git remote show origin
cd /D/workspace_python/githubRepo/Infinity/


#git push -u origin main
# 定义最大重试次数和间隔时间
MAX_RETRIES=6
RETRY_INTERVAL=600 # 单位：秒（10分钟）

# 初始化变量
retry_count=0
push_success=false

# 循环执行 git push
while [ $retry_count -lt $MAX_RETRIES ]; do
    echo "Attempt $(($retry_count + 1)) of $MAX_RETRIES: Trying to push to GitHub..."

    # 执行 git push（HEAD:main 无论本地分支叫什么名字都推到远程 main，
    # 避免远程默认分支调整后 "src refspec main does not match any"）
    push_output=$(git push -u origin HEAD:main 2>&1)
    push_exit=$?
    echo "$push_output"
    if [ $push_exit -eq 0 ]; then
        echo "Push successful!"
        push_success=true
        break
    else
        # 远程 main 有本地没有的提交（fetch first / non-fast-forward）：
        # 这种错误重试无效。GitHub 端只是 gitee 的镜像，
        # 用 ours 策略合并（保留本地内容、把远程提交记为已合并）后立刻重推
        if echo "$push_output" | grep -q "fetch first\|non-fast-forward"; then
            echo "Remote main has new commits, merging origin/main with ours strategy..."
            git merge --abort 2>/dev/null
            if git fetch origin main && git merge --allow-unrelated-histories -s ours origin/main; then
                echo "Merge done, retrying push immediately..."
                retry_count=$((retry_count + 1))
                continue    # 立刻重推，不 sleep（仍计入次数防死循环）
            else
                echo "Merge failed — 需人工处理后再运行脚本"
                git merge --abort 2>/dev/null
            fi
        fi
        echo "Push failed. Retrying in $RETRY_INTERVAL seconds..."
        retry_count=$((retry_count + 1))
        sleep $RETRY_INTERVAL
    fi
done

# 如果所有重试都失败，则输出错误信息
if [ "$push_success" = false ]; then
    echo "All attempts failed. Please check your network or repository settings."
fi

echo "----Ended----"

#read -p "按回车键继续..."