[Setup]
AppName=Muse
AppVersion=1.1.2
DefaultDirName={pf}\Muse
DefaultGroupName=Muse
OutputDir=.
OutputBaseFilename=MuseSetup-v1.1.2

[Files]
Source: "dist\muse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Muse"; Filename: "{app}\muse.exe"

[Code]
const
  WM_SETTINGCHANGE = $1A;
  SMTO_ABORTIFHUNG = $0002;

function SendMessageTimeout(hWnd: Integer; Msg: Integer; wParam: Integer; lParam: String; fuFlags: Integer; uTimeout: Integer; var lpdwResult: Integer): Integer;
  external 'SendMessageTimeoutW@user32.dll stdcall';

procedure AddToPath();
var
  Path: string;
  ResultVal: Integer;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    Path := '';
  if Pos(ExpandConstant('{app}'), Path) = 0 then
  begin
    if (Length(Path) > 0) and (Path[Length(Path)] <> ';') then
      Path := Path + ';';
    Path := Path + ExpandConstant('{app}');
    RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path);
    SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, ResultVal);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpFinished then
    AddToPath();
  Result := True;
end;