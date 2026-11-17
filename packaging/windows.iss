#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif

#define AppName "Step to Transcriber"
#define AppExe AppName + ".exe"

[Setup]
AppId={{C27F3ADA-DFB8-4843-8CFD-1754E45316A8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Steptovictory
AppPublisherURL=https://github.com/steptovictory-dev
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\{#AppExe}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.17763
SetupIconFile=..\assets\step-to-transcriber.ico
OutputBaseFilename=Step-to-Transcriber-{#AppVersion}-Windows-x64-Setup
Compression=lzma2/fast
SolidCompression=yes
LZMAUseSeparateProcess=yes
RestartApplications=no
WizardStyle=modern dark hidebevels
WizardBackColor=#22211f
WizardImageFile=..\assets\step-to-transcriber.png
WizardSmallImageFile=..\assets\step-to-transcriber.png

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\step-to-transcriber.png"; DestDir: "{app}\_internal\assets"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "Steptovictory.StepToTranscriber"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "Steptovictory.StepToTranscriber"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Messages]
en.ConfirmUninstall=Remove %1 from this computer?%n%nYour transcripts, settings, logs, and downloaded models will be kept.
ru.ConfirmUninstall=Удалить %1 с этого компьютера?%n%nРасшифровки, настройки, журналы и загруженные модели сохранятся.

[Code]
procedure StyleHeading(Heading: TNewStaticText);
begin
  if HighContrastActive then
    Exit;
  Heading.StyleElements := Heading.StyleElements - [seFont];
  Heading.Font.Name := 'Georgia';
  Heading.Font.Color := StrToColor('#DF9B66');
  Heading.Font.Style := [fsBold, fsItalic];
end;

procedure SquareBrandImage(BrandImage: TBitmapImage);
begin
  BrandImage.Top := BrandImage.Top + (BrandImage.Height - BrandImage.Width) div 2;
  BrandImage.Height := BrandImage.Width;
end;

procedure InitializeWizard;
begin
  StyleHeading(WizardForm.WelcomeLabel1);
  StyleHeading(WizardForm.PageNameLabel);
  StyleHeading(WizardForm.FinishedHeadingLabel);
  SquareBrandImage(WizardForm.WizardBitmapImage);
  SquareBrandImage(WizardForm.WizardBitmapImage2);
end;

procedure InitializeUninstallProgressForm;
var
  BrandImage: String;
begin
  StyleHeading(UninstallProgressForm.PageNameLabel);
  BrandImage := ExpandConstant('{app}\_internal\assets\step-to-transcriber.png');
  if FileExists(BrandImage) then
  begin
    try
      UninstallProgressForm.WizardSmallBitmapImage.PngImage.LoadFromFile(BrandImage);
    except
      Log('Could not load the uninstall logo.');
    end;
  end;
end;
