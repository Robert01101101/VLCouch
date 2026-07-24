; VLCouch Windows installer — compile with: iscc /DAppVersion=x.y.z install\VLCouch.iss

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define MyAppName "VLCouch"
#define MyAppPublisher "VLCouch"
#define MyAppURL "https://github.com/Robert01101101/VLCouch"
#define MyAppExeName "launch.vbs"
#define StagingDir "..\dist\staging"
#define DataDir "{localappdata}\VLCouch\data"

[Setup]
AppId={{A7B3C4D5-E6F7-4890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\VLCouch\app
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=VLCouchSetup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\vlcouch.ico
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StagingDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\vlcouch.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\vlcouch.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure StopVlcouchServer();
var
  ResultCode: Integer;
begin
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -Command "' +
    '$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ' +
    'Where-Object { $_.LocalAddress -in @(''127.0.0.1'', ''0.0.0.0'', ''::'') }; ' +
    'foreach ($conn in $conns) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }; ' +
    '$procs = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like ''*VLCouch*'' }; ' +
    'foreach ($proc in $procs) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  StopVlcouchServer();
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  StopVlcouchServer();
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox(
      'Your library database, posters, and settings are stored separately and were not removed.' + #13#10 + #13#10 +
      'Data folder:' + #13#10 +
      ExpandConstant('{localappdata}\VLCouch\data') + #13#10 + #13#10 +
      'Delete this folder too?',
      mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{localappdata}\VLCouch\data'), True, True, True);
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    ForceDirectories(ExpandConstant('{#DataDir}'));
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    ForceDirectories(ExpandConstant('{#DataDir}'));
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nYour media library data is stored separately in %LOCALAPPDATA%\VLCouch\data and is preserved when you upgrade.
