# 用 PowerPoint 把模板匯出成圖片：每一張現有投影片、以及每一種版面（空白套一次）各一張 PNG。
#   powershell -ExecutionPolicy Bypass -File scripts\pptx_export.ps1 -Src <template.pptx> -OutDir <dir>
# 只讀原檔：版面那批是在暫存副本上加投影片再匯出，原檔不會被改。
param([string]$Src, [string]$OutDir)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$tmp = Join-Path $env:TEMP ("deckvideo_" + [guid]::NewGuid().ToString() + ".pptx")
Copy-Item $Src $tmp
$app = New-Object -ComObject PowerPoint.Application
try {
  $pres = $app.Presentations.Open($tmp, $false, $false, $false)   # 可寫的暫存副本、不開視窗
  $w = 1920; $h = [int](1920 * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
  $n = $pres.Slides.Count
  for ($i = 1; $i -le $n; $i++) { $pres.Slides.Item($i).Export((Join-Path $OutDir ("slide{0:D2}.png" -f $i)), "PNG", $w, $h) }
  $k = 0
  foreach ($design in $pres.Designs) {
    foreach ($layout in $design.SlideMaster.CustomLayouts) {
      $k++
      $s = $pres.Slides.AddSlide($pres.Slides.Count + 1, $layout)
      $safe = ($layout.Name -replace '[^\w\-]', '_')
      $s.Export((Join-Path $OutDir ("layout{0:D2}_{1}.png" -f $k, $safe)), "PNG", $w, $h)
    }
  }
  "slides=$n layouts=$k size=${w}x${h}"
  $pres.Close()
} finally {
  $app.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
  Remove-Item $tmp -ErrorAction SilentlyContinue
}
