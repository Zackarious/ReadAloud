; Inno Setup 6 Script for ReadAloud
; Generates ReadAloud-1.8.19-Windows-Setup-x64.exe

#define MyAppName "ReadAloud"
#define MyAppVersion "1.8.19"
#define MyAppPublisher "zackarious"
#define MyAppURL "https://github.com/Zackarious/ReadAloud"
#define MyAppExeName "ReadAloud.exe"

[Setup]
AppId={{D3F9E17A-5F7B-4B7C-8A9E-3E4F6B8A2C1D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=ReadAloud-1.8.19-Windows-Setup-x64
SetupIconFile=ReadAloud.ico
Compression=lzma2/ultra64
SolidCompression=yes
DiskSpanning=yes
DiskSliceSize=1800000000
SlicesPerDisk=1
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SelectDiskTitle=Setup Needs the Next Installation Component
SelectDiskLabel=Please ensure 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%1.bin' is in the folder below and click OK.
SelectDiskLabel2=Setup needs the next installation component file (Part %1).%n%nPlease ensure 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%1.bin' is located in the folder displayed below, or click Browse to select it.%n%nIf you have not downloaded Part %1 yet, download 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%1.bin' from {#MyAppURL}/releases/tag/v{#MyAppVersion} into that folder.
FileNotInDir2=The file "%1" could not be located in "%2". Please download 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%1.bin' from {#MyAppURL}/releases/tag/v{#MyAppVersion} into that folder.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Standalone application bundle files (including bundled voice models and runtimes)
Source: "..\dist\ReadAloud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ReadAloud.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ReadAloud.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  TotalSlices = 2;

var
  DownloadPage: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax <> 0 then
    Log(Format('Download progress for %s: %d of %d bytes', [FileName, Progress, ProgressMax]))
  else
    Log(Format('Download progress for %s: %d bytes', [FileName, Progress]));
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'Downloading Missing Installation Components',
    'Please wait while Setup downloads the required installation data files from GitHub...',
    @OnDownloadProgress
  );
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  I: Integer;
  BinFileName: String;
  BinPath: String;
  TmpPath: String;
  DownloadUrl: String;
  MissingList: String;
  MissingCount: Integer;
  MissingSlices: array[1..TotalSlices] of Boolean;
  Success: Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    MissingCount := 0;
    MissingList := '';
    for I := 1 to TotalSlices do
    begin
      BinFileName := Format('ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%d.bin', [I]);
      BinPath := ExpandConstant('{src}\' + BinFileName);
      if not FileExists(BinPath) then
      begin
        MissingSlices[I] := True;
        MissingCount := MissingCount + 1;
        MissingList := MissingList + '  • ' + BinFileName + #13#10;
      end
      else
      begin
        MissingSlices[I] := False;
      end;
    end;

    if MissingCount > 0 then
    begin
      if MsgBox(
        'Setup detected that ' + IntToStr(MissingCount) + ' required installation component file(s) are missing from this folder:' + #13#10#13#10 +
        MissingList + #13#10 +
        'Because ReadAloud bundles offline neural speech models, the installer package is split across multiple files.' + #13#10#13#10 +
        'Would you like Setup to automatically download the missing file(s) for you from GitHub now?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        DownloadPage.Clear;
        for I := 1 to TotalSlices do
        begin
          if MissingSlices[I] then
          begin
            BinFileName := Format('ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%d.bin', [I]);
            DownloadUrl := '{#MyAppURL}/releases/download/v{#MyAppVersion}/' + BinFileName;
            DownloadPage.Add(DownloadUrl, BinFileName, '');
          end;
        end;

        DownloadPage.Show;
        try
          try
            DownloadPage.Download;
            for I := 1 to TotalSlices do
            begin
              if MissingSlices[I] then
              begin
                BinFileName := Format('ReadAloud-{#MyAppVersion}-Windows-Setup-x64-%d.bin', [I]);
                BinPath := ExpandConstant('{src}\' + BinFileName);
                TmpPath := ExpandConstant('{tmp}\' + BinFileName);
                if FileExists(TmpPath) then
                begin
                  Success := FileCopy(TmpPath, BinPath, False);
                  if not Success then
                  begin
                    MsgBox(
                      'Component ' + BinFileName + ' was downloaded to your temporary folder:' + #13#10 +
                      TmpPath + #13#10#13#10 +
                      'However, Setup could not write directly to the installer folder.' + #13#10 +
                      'Please select this temporary folder if prompted during file extraction.',
                      mbInformation, MB_OK);
                  end;
                end;
              end;
            end;
          except
            MsgBox(
              'Automatic download failed: ' + GetExceptionMessage + #13#10#13#10 +
              'Please manually download the missing files from:' + #13#10 +
              '{#MyAppURL}/releases/tag/v{#MyAppVersion}' + #13#10#13#10 +
              'and place them in the same folder as this installer before running it again.',
              mbError, MB_OK);
            Result := False;
          end;
        finally
          DownloadPage.Hide;
        end;
      end
      else
      begin
        MsgBox(
          'Installation cannot proceed without all required component files.' + #13#10#13#10 +
          'Please download both setup parts from:' + #13#10 +
          '{#MyAppURL}/releases/tag/v{#MyAppVersion}' + #13#10#13#10 +
          'and place them in the same folder before launching Setup.',
          mbInformation, MB_OK);
        Result := False;
      end;
    end;
  end;
end;
