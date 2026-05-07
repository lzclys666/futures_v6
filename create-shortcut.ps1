$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\futures_v6启动.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"D:\futures_v6\start-all.ps1`""
$Shortcut.WorkingDirectory = "D:\futures_v6"
$Shortcut.Description = "一键启动 futures_v6 后端+前端"
$Shortcut.Save()
Write-Host "Shortcut created: $Desktop\futures_v6启动.lnk"
