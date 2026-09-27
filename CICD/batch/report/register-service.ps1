$action = New-ScheduledTaskAction -Execute "D:\workspace_python\infinity\CICD\batch\report\run_reports.bat" -WorkingDirectory "D:\workspace_python\infinity\CICD\batch\data"
$triggerSat = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "13:00"
Register-ScheduledTask -TaskName "infinity_run_reports" -Action $action -Trigger $triggerSat -Force

schtasks /Query /TN "infinity_run_reports" /FO LIST
