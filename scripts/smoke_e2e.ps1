# Stage-1 E2E via Node BFF (Python must be on :8000, BFF on :3001)
$ErrorActionPreference = "Stop"
$bff = "http://127.0.0.1:3001/api"

Write-Host "health..."
Invoke-RestMethod "$bff/health" | Out-Null

Write-Host "refresh..."
Invoke-RestMethod -Method Post "$bff/trends/refresh" | Out-Null

$trends = Invoke-RestMethod "$bff/trends"
if (-not $trends -or $trends.Count -lt 1) { throw "no trends" }
$tid = $trends[0].id
Write-Host "trend=$tid"

$preset = Invoke-RestMethod -Method Post "$bff/trends/$tid/build-preset"
Write-Host "preset=$($preset.id)"

$pngPath = Join-Path $env:TEMP "face_smoke.png"
[IO.File]::WriteAllBytes(
  $pngPath,
  [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
)

$curl = curl.exe -s -X POST "$bff/generate" -F "preset_id=$($preset.id)" -F "face=@$pngPath;type=image/png"
$job = $curl | ConvertFrom-Json
if ($job.status -ne "done") { throw "job not done: $($job | ConvertTo-Json -Compress)" }
if (-not $job.mocked) { Write-Host "warning: mocked=false (ok for stage 2)" }

$art = Invoke-WebRequest "$bff/artifacts/$($job.output_path)" -UseBasicParsing
if ($art.StatusCode -ne 200) { throw "artifact failed" }

Write-Host "SMOKE OK job=$($job.id) bytes=$($art.RawContentLength) mocked=$($job.mocked)"
