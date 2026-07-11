Option Explicit

' VLCouch shortcut entry point — resolves paths from this script's folder so
' shortcuts keep working after the repo is moved or renamed.
Dim fso, shell, scriptDir, startPs1, cmd, exitCode

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
startPs1 = scriptDir & "\start.ps1"

If Not fso.FileExists(startPs1) Then
    shell.Popup _
        "VLCouch could not find start.ps1 at:" & vbCrLf & startPs1 & vbCrLf & vbCrLf & _
        "Run setup from the project folder:" & vbCrLf & "  .\scripts\install-shortcuts.ps1", _
        0, "VLCouch", 16
    WScript.Quit 1
End If

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & startPs1 & """"
exitCode = shell.Run(cmd, 0, True)

' start.ps1 uses exit code 2 when it already showed a message box.
If exitCode = 2 Then
    WScript.Quit exitCode
End If

If exitCode <> 0 Then
    shell.Popup _
        "VLCouch failed to start (exit code " & exitCode & ")." & vbCrLf & vbCrLf & _
        "Run setup from the project folder:" & vbCrLf & "  .\scripts\install-shortcuts.ps1", _
        0, "VLCouch", 16
End If

WScript.Quit exitCode
