#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif

#define AppName "Step to Transcriber"
#ifdef OnlineInstaller
  #define AppExe "python\pythonw.exe"
#else
#define AppExe AppName + ".exe"
#endif

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
#ifdef OnlineInstaller
UninstallDisplayIcon={app}\app\assets\step-to-transcriber.ico
SetupLogging=yes
#else
UninstallDisplayIcon={app}\{#AppExe}
#endif
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.17763
SetupIconFile=..\assets\step-to-transcriber.ico
#ifdef OnlineInstaller
OutputBaseFilename=Step-to-Transcriber-{#AppVersion}-Windows-x64-Web-Setup
#else
OutputBaseFilename=Step-to-Transcriber-{#AppVersion}-Windows-x64-Setup
#endif
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
#ifdef OnlineInstaller
Source: "{#RuntimeDir}\*"; DestDir: "{tmp}\runtime"; Flags: dontcopy noencryption recursesubdirs
Source: "windows-online-requirements.txt"; DestDir: "{tmp}"; Flags: dontcopy noencryption
Source: "{tmp}\runtime\*"; DestDir: "{app}\python"; Flags: external ignoreversion recursesubdirs createallsubdirs
Source: "{#BundleDir}\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\step-to-transcriber.png"; DestDir: "{app}\_internal\assets"; Flags: ignoreversion
#endif

[Icons]
#ifdef OnlineInstaller
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "-B ""{app}\app\app.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\assets\step-to-transcriber.ico"; AppUserModelID: "Steptovictory.StepToTranscriber"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "-B ""{app}\app\app.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\assets\step-to-transcriber.ico"; Tasks: desktopicon; AppUserModelID: "Steptovictory.StepToTranscriber"
#else
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "Steptovictory.StepToTranscriber"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "Steptovictory.StepToTranscriber"
#endif

[Run]
#ifdef OnlineInstaller
Filename: "{app}\{#AppExe}"; Parameters: "-B ""{app}\app\app.py"""; WorkingDir: "{app}\app"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
#else
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
#endif

[Messages]
en.ConfirmUninstall=Remove %1 from this computer?%n%nYour transcripts, settings, logs, and downloaded models will be kept.
ru.ConfirmUninstall=Удалить %1 с этого компьютера?%n%nРасшифровки, настройки, журналы и загруженные модели сохранятся.

#ifdef OnlineInstaller
[CustomMessages]
en.RuntimeTitle=Downloading application libraries
en.RuntimeDescription=Setup downloads the required libraries from PyPI.
en.RuntimeWait=Keep the internet connection open. This can take several minutes.
en.RuntimeFailure=Setup could not prepare the application libraries. Check your internet connection and free disk space, then try again.%n%nSetup log: %1
ru.RuntimeTitle=Скачивание библиотек приложения
ru.RuntimeDescription=Установщик скачивает необходимые библиотеки с PyPI.
ru.RuntimeWait=Оставьте подключение к интернету включённым. Это может занять несколько минут.
ru.RuntimeFailure=Не удалось подготовить библиотеки приложения. Проверьте интернет и свободное место на диске, затем повторите установку.%n%nЖурнал установки: %1
#endif

[Code]
#ifdef OnlineInstaller
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Progress: TOutputProgressWizardPage;
  Runtime, Params: String;
  ExitCode: Integer;
begin
  Result := FmtMessage(CustomMessage('RuntimeFailure'), [ExpandConstant('{log}')]);
  Progress := CreateOutputProgressPage(CustomMessage('RuntimeTitle'), CustomMessage('RuntimeDescription'));
  Progress.SetText(CustomMessage('RuntimeWait'), '');
  Progress.SetProgress(0, 0);
  Progress.Show;
  try
    try
      ExtractTemporaryFiles('{tmp}\runtime\*');
      ExtractTemporaryFile('windows-online-requirements.txt');
      Runtime := ExpandConstant('{tmp}\runtime');
      Params := '-m pip --isolated install' +
        ' --no-input --disable-pip-version-check --no-cache-dir --no-compile --only-binary=:all:' +
        ' --index-url https://pypi.org/simple --progress-bar off --require-hashes' +
        ' --target "' + Runtime + '\Lib\site-packages"' +
        ' --requirement "' + ExpandConstant('{tmp}\windows-online-requirements.txt') + '"';
      if ExecAndLogOutput(Runtime + '\python.exe', Params, Runtime, SW_SHOWNORMAL,
        ewWaitUntilTerminated, ExitCode, nil) and (ExitCode = 0) then
      begin
        { Use the matched cuDNN runtime from the NVIDIA wheel. }
        DeleteFile(Runtime + '\Lib\site-packages\ctranslate2\cudnn64_9.dll');
        Result := '';
      end;
    except
      Log(GetExceptionMessage);
    end;
  finally
    Progress.Hide;
  end;
end;
#endif

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
#ifdef OnlineInstaller
  BrandImage := ExpandConstant('{app}\app\assets\step-to-transcriber.png');
#else
  BrandImage := ExpandConstant('{app}\_internal\assets\step-to-transcriber.png');
#endif
  if FileExists(BrandImage) then
  begin
    try
      UninstallProgressForm.WizardSmallBitmapImage.PngImage.LoadFromFile(BrandImage);
    except
      Log('Could not load the uninstall logo.');
    end;
  end;
end;
