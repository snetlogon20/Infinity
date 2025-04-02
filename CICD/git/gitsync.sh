###################
# gitee 手工提交
# /D/workspace_python/infinity/CICD/git/gitsync.sh
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

    # 执行 git push
    if git push -u origin main; then
        echo "Push successful!"
        push_success=true
        break
    else
        echo "Push failed. Retrying in $RETRY_INTERVAL seconds..."
        retry_count=$((retry_count + 1))
        sleep $RETRY_INTERVAL
    fi
done

# 如果所有重试都失败，则输出错误信息
if [ "$push_success" = false ]; then
    echo "All attempts failed. Please check your network or repository settings."
fi