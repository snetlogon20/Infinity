$action = New-ScheduledTaskAction -Execute "D:\workspace_python\infinity\CICD\batch\report\run_reports.bat" -WorkingDirectory "D:\workspace_python\infinity\CICD\batch\data"
$triggerSat = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "13:00"
Register-ScheduledTask -TaskName "RunReports" -Action $action -Trigger $triggerSat -Force

schtasks /Query /TN "RunReports" /FO LIST
