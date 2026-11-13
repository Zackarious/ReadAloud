; Inno Setup 6 Script for ReadAloud
; Generates ReadAloud-1.8.18-Windows-Setup-x64.exe

#define MyAppName "ReadAloud"
#define MyAppVersion "1.8.18"
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
OutputBaseFilename=ReadAloud-1.8.18-Windows-Setup-x64
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
DiskInsert=Setup needs the next required installation component file (%1).%n%nPlease ensure 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-1.bin' is located in the same folder as this installer.%n%nIf the file is located in another folder, enter the path below or click Browse.

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
    'Downloading Missing Installation Component',
    'Please wait while Setup downloads the required installation data file from GitHub...',
    @OnDownloadProgress
  );
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  BinFileName: String;
  BinPath: String;
  TmpPath: String;
  DownloadUrl: String;
  Success: Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    BinFileName := 'ReadAloud-{#MyAppVersion}-Windows-Setup-x64-1.bin';
    BinPath := ExpandConstant('{src}\' + BinFileName);
    
    if not FileExists(BinPath) then
    begin
      if MsgBox(
        'Setup detected that a required installation component is missing from this folder:' + #13#10#13#10 +
        '  ' + BinFileName + #13#10#13#10 +
        'Because ReadAloud bundles offline neural speech models, the installer package is split across multiple files.' + #13#10#13#10 +
        'Would you like Setup to automatically download the missing file for you from GitHub now?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        DownloadPage.Clear;
        DownloadUrl := '{#MyAppURL}/releases/download/v{#MyAppVersion}/' + BinFileName;
        DownloadPage.Add(DownloadUrl, BinFileName, '');
        DownloadPage.Show;
        try
          try
            DownloadPage.Download;
            TmpPath := ExpandConstant('{tmp}\' + BinFileName);
            if FileExists(TmpPath) then
            begin
              Success := FileCopy(TmpPath, BinPath, False);
              if not Success then
              begin
                MsgBox(
                  'The component was downloaded to your temporary folder:' + #13#10 +
                  TmpPath + #13#10#13#10 +
                  'However, Setup could not write directly to the installer folder.' + #13#10 +
                  'Please select this temporary folder if prompted during file extraction.',
                  mbInformation, MB_OK);
              end;
            end;
          except
            MsgBox(
              'Automatic download failed: ' + GetExceptionMessage + #13#10#13#10 +
              'Please manually download ' + BinFileName + ' from:' + #13#10 +
              '{#MyAppURL}/releases/tag/v{#MyAppVersion}' + #13#10#13#10 +
              'and place it in the same folder as this installer before running it again.',
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
          'Installation cannot proceed without ' + BinFileName + '.' + #13#10#13#10 +
          'Please download both setup parts from:' + #13#10 +
          '{#MyAppURL}/releases/tag/v{#MyAppVersion}' + #13#10#13#10 +
          'and place them in the same folder before launching Setup.',
          mbInformation, MB_OK);
        Result := False;
      end;
    end;
  end;
end;
