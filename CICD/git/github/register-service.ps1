# ============================================================
# git 同步计划任务注册脚本（参照 CICD/batch/data/register-service.ps1）
# 作用：把 github_sync.bat（gitee -> github 定时同步）注册为 Windows 计划任务
#       触发频率与 infinity_gitbash_githuib_sync.xml 保持一致：每周六 22:00
# 执行：右键"使用 PowerShell 运行"或 powershell -ExecutionPolicy Bypass -File register-service.ps1
# ============================================================

$action = New-ScheduledTaskAction -Execute "D:\workspace_python\infinity\CICD\git\github\github_sync.bat" -WorkingDirectory "D:\workspace_python\infinity\CICD\git\github"
$triggerSat = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "22:00"
Register-ScheduledTask -TaskName "infinity_gitbash_github_sync" -Action $action -Trigger $triggerSat -Force

schtasks /Query /TN "infinity_gitbash_github_sync" /FO LIST
