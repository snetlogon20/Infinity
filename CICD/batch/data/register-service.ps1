$action = New-ScheduledTaskAction -Execute "D:\workspace_python\infinity\CICD\batch\data\run_DataRefreshManager.bat" -WorkingDirectory "D:\workspace_python\infinity\CICD\batch\data"
$triggerFri = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At "22:00"
$triggerSat = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "12:00"
Register-ScheduledTask -TaskName "infinity_refresh_data" -Action $action -Trigger $triggerFri, $triggerSat -Force

schtasks /Query /TN "infinity_refresh_data" /FO LIST