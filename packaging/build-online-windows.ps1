[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PythonZip,
    [Parameter(Mandatory)]
    [string]$PipWheel,
    [Parameter(Mandatory)]
    [string]$NodeDist,
    [string]$Iscc = 'ISCC.exe',
    [ValidatePattern('^\d+\.\d+\.\d+(-[A-Za-z0-9]+([.-][A-Za-z0-9]+)*)?$')]
    [string]$Version = '0.1.0'
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$pythonArchive = (Resolve-Path -LiteralPath $PythonZip).Path
$pip = (Resolve-Path -LiteralPath $PipWheel).Path
$node = (Resolve-Path -LiteralPath $NodeDist).Path
$compiler = (Get-Command -Name $Iscc -CommandType Application).Source
$buildRoot = (New-Item -ItemType Directory -Force -Path (Join-Path $project 'build')).FullName
$work = (New-Item -ItemType Directory -Path (Join-Path $buildRoot ([guid]::NewGuid()))).FullName

try {
    $runtime = Join-Path $work 'python'
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $runtime
    $python = Join-Path $runtime 'python.exe'
    $paths = Join-Path $runtime 'python314._pth'
    if (-not (Test-Path -LiteralPath $paths -PathType Leaf)) {
        throw 'Use the official Windows x64 Python 3.14 embeddable archive.'
    }
    @('python314.zip', '.', 'Lib\site-packages', '..\app', 'import site') |
        Set-Content -LiteralPath $paths -Encoding ascii
    [IO.Compression.ZipFile]::ExtractToDirectory($pip, (Join-Path $runtime 'Lib\site-packages'))
    & $python -c "import platform,sys; sys.exit(platform.machine() != 'AMD64' or sys.maxsize < 2**32)"
    if ($LASTEXITCODE) { throw 'The embedded Python interpreter must be Windows x64.' }
    & $python -m pip --version
    if ($LASTEXITCODE) { throw 'The bundled pip wheel did not start.' }

    $app = (New-Item -ItemType Directory -Path (Join-Path $work 'app')).FullName
    foreach ($directory in @('src', 'assets', 'tools')) {
        New-Item -ItemType Directory -Path (Join-Path $app $directory) | Out-Null
    }
    foreach ($file in @('app.py', 'LICENSE', 'assets\checkmark.svg', 'assets\step-to-transcriber.ico', 'assets\step-to-transcriber.png')) {
        Copy-Item -LiteralPath (Join-Path $project $file) -Destination (Join-Path $app $file)
    }
    foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $project 'src') -File -Filter '*.py')) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $app 'src')
    }
    foreach ($file in @('node.exe', 'LICENSE')) {
        Copy-Item -LiteralPath (Join-Path $node $file) -Destination (Join-Path $app 'tools')
    }
    New-Item -ItemType File -Path (Join-Path $app 'installed.flag') | Out-Null

    & $compiler '/DOnlineInstaller=1' "/DAppVersion=$Version" "/DBundleDir=$app" "/DRuntimeDir=$runtime" "/O$work" (Join-Path $PSScriptRoot 'windows.iss')
    if ($LASTEXITCODE) { throw 'Inno Setup failed.' }
    $name = "Step-to-Transcriber-$Version-Windows-x64-Web-Setup.exe"
    $dist = (New-Item -ItemType Directory -Force -Path (Join-Path $project 'dist')).FullName
    $destination = Join-Path $dist $name
    Move-Item -LiteralPath (Join-Path $work $name) -Destination $destination -Force
    Get-FileHash -LiteralPath $destination -Algorithm SHA256
}
finally {
    if ([IO.Path]::GetDirectoryName($work) -eq $buildRoot) {
        Remove-Item -LiteralPath $work -Recurse -Force
    }
}
