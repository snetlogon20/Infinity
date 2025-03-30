###################
# gitee 手工提交
# /D/workspace_python/infinity/CICD/git/gitsync.sh
###################

mkdir -p /D/workspace_python/giteeRepo/
cd /D/workspace_python/giteeRepo/
rm -rf /D/workspace_python/giteeRepo/infinity/
git clone https://gitee.com/snetlogon20/infinity

#cd /D/workspace_python/giteeRepo/infinity/Infinity/
#git pull origin main

mkdir -p /D/workspace_python/githubRepo/Infinity/
cd /D/workspace_python/githubRepo/Infinity/
rm -rf /D/workspace_python/githubRepo/Infinity/CICD
rm -rf /D/workspace_python/githubRepo/Infinity/dataIntegrator
cp -r /D/workspace_python/giteeRepo/infinity/CICD /D/workspace_python/githubRepo/Infinity
cp -r /D/workspace_python/giteeRepo/infinity/dataIntegrator /D/workspace_python/githubRepo/Infinity

cd /D/workspace_python/githubRepo/Infinity/

git status
git add .
git status
git commit -m "repo sync"
git remote set-url origin https://github.com/snetlogon20/Infinity.git
git push -u origin main