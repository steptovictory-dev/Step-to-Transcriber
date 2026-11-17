[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$NodeDist,
    [string]$Python = '.\.venv\Scripts\python.exe',
    [string]$Iscc = 'ISCC.exe',
    [ValidatePattern('^\d+\.\d+\.\d+(-[A-Za-z0-9]+([.-][A-Za-z0-9]+)*)?$')]
    [string]$Version = '0.1.0'
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$pythonPath = (Get-Command -Name $Python -CommandType Application -ErrorAction Stop).Source
$isccPath = (Get-Command -Name $Iscc -CommandType Application -ErrorAction Stop).Source
$nodePath = (Resolve-Path -LiteralPath $NodeDist).Path

foreach ($file in @('node.exe', 'LICENSE')) {
    if (-not (Test-Path -LiteralPath (Join-Path $nodePath $file) -PathType Leaf)) {
        throw "Supply an extracted official Node.js Windows x64 archive with $file."
    }
}
& $pythonPath -c "import platform, sys; sys.exit(platform.system() != 'Windows' or platform.machine() != 'AMD64' or sys.maxsize < 2**32)"
if ($LASTEXITCODE -ne 0) { throw 'Build with 64-bit x86 Python on Windows.' }

$buildRoot = (New-Item -ItemType Directory -Force -Path (Join-Path $project 'build')).FullName
$work = (New-Item -ItemType Directory -Path (Join-Path $buildRoot ([guid]::NewGuid()))).FullName
$dist = (New-Item -ItemType Directory -Force -Path (Join-Path $project 'dist')).FullName
$previousNode = $env:TRANSCRIBER_NODE_DIST
try {
    $env:TRANSCRIBER_NODE_DIST = $nodePath
    & $pythonPath -m PyInstaller --noconfirm --distpath $work --workpath (Join-Path $work 'work') (Join-Path $PSScriptRoot 'windows.spec')
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

    $bundle = Join-Path $work 'Step to Transcriber'
    & $isccPath "/DAppVersion=$Version" "/DBundleDir=$bundle" "/O$work" (Join-Path $PSScriptRoot 'windows.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed.' }

    $name = "Step-to-Transcriber-$Version-Windows-x64-Setup.exe"
    $installer = Get-Item -LiteralPath (Join-Path $work $name)
    if ($installer.Length -ge 2GB) { throw 'The installer exceeds the GitHub Releases file size limit.' }
    $destination = Join-Path $dist $name
    Move-Item -LiteralPath $installer.FullName -Destination $destination -Force
    Get-FileHash -LiteralPath $destination -Algorithm SHA256
}
finally {
    $env:TRANSCRIBER_NODE_DIST = $previousNode
    if ([IO.Path]::GetDirectoryName($work) -eq $buildRoot) {
        Remove-Item -LiteralPath $work -Recurse -Force
    }
}
