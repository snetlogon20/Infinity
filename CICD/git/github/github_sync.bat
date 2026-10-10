@echo off
rem ============================================================
rem github_sync.bat - gitee -> github 定时同步入口
rem 由计划任务 infinity_gitbash_github_sync 调用（见 register-service.ps1）
rem
rem 修复说明：
rem   1. 原写法 "--cd-to-home /D/.../github_sync.sh" 有两个问题：
rem      a) --cd-to-home 会把工作目录切到 HOME，与后面的脚本路径参数冲突
rem      b) github_sync.sh 不存在，实际同步脚本是 gitsync.sh
rem   2. gitsync.sh 内部全部使用绝对路径，无需依赖工作目录
rem ============================================================

"C:\Program Files\Git\git-bash.exe" -c "bash /D/workspace_python/infinity/CICD/git/github/gitsync.sh"

exit /b %ERRORLEVEL%
