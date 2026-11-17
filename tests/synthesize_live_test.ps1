# Generate a local control recording without playing it
$testDirectory = Join-Path $PSScriptRoot '../../output/live_smoke'
New-Item -ItemType Directory -Force -Path $testDirectory | Out-Null
$testPath = [IO.Path]::GetFullPath((Join-Path $testDirectory 'control_speech.wav'))
$testVoice = New-Object -ComObject SAPI.SpVoice
$testStream = New-Object -ComObject SAPI.SpFileStream
try {
    $testStream.Open($testPath, 3)
    $testVoice.AudioOutputStream = $testStream
    $testVoice.Speak('This is a live transcription test. The application receives sound from the default Windows audio device. Recognized words are saved while the session is running. We can change the audio device without starting a new session.') | Out-Null
}
finally {
    $testStream.Close()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($testStream) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($testVoice) | Out-Null
}
Write-Output $testPath
