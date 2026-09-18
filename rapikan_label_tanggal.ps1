$p = "templates\pelanggan_tambah.html"

Copy-Item $p "$p.sebelum_rapikan_label.bak" -Force

$s = Get-Content $p -Raw

$s = $s.Replace(
    "FORMAT: MM/DD/YYYY",
    "FORMAT: DD/MM/YYYY"
)

$s = $s.Replace(
    'placeholder="MM/DD/YYYY"',
    'placeholder="DD/MM/YYYY"'
)

$s = $s.Replace(
    "Format: MM/DD/YYYY.",
    "Format: DD/MM/YYYY."
)

$s = $s.Replace(
    "Format Jatuh Tempo harus MM/DD/YYYY.",
    "Format Jatuh Tempo harus DD/MM/YYYY."
)

Set-Content $p $s -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " OK - LABEL TANGGAL DIRAPIKAN"
Write-Host " FORMAT RESMI: DD/MM/YYYY"
Write-Host "=========================================="
