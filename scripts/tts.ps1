# 用 Windows 內建的 SAPI 產旁白。完全離線 —— 文字不會離開這台機器。
# 由 scripts/deck.py（engine = sapi）呼叫：
#   powershell -ExecutionPolicy Bypass -File scripts\tts.ps1 -SpecPath <spec.json> -OutDir <輸出資料夾>
# spec.json：{ "voice": "...", "rate": 0, "lines": [{ "id": "...", "text": "..." }] }，產出 <OutDir>/<id>.wav。
param([Parameter(Mandatory = $true)][string]$SpecPath, [Parameter(Mandatory = $true)][string]$OutDir)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$spec = Get-Content (Join-Path $root $SpecPath) -Raw -Encoding UTF8 | ConvertFrom-Json
$outDir = Join-Path $root $OutDir
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($spec.voice)
$synth.Rate = $spec.rate

foreach ($line in $spec.lines) {
    $wav = Join-Path $outDir "$($line.id).wav"
    $synth.SetOutputToWaveFile($wav)
    $synth.Speak($line.text)
    $synth.SetOutputToNull()
    "{0,-10} {1,8:N0} bytes" -f $line.id, (Get-Item $wav).Length
}

$synth.Dispose()
