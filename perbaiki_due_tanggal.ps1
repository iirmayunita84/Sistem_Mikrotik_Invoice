$p = "templates\pelanggan_tambah.html"

$lines = [System.Collections.Generic.List[string]](Get-Content $p)

# Cari awal blok FORMAT BARU
$start = -1

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match 'FORMAT BARU:') {
        $start = $i
        break
    }
}

if ($start -lt 0) {
    throw "BLOK FORMAT BARU TIDAK DITEMUKAN"
}

# Cari penutup blok utama dalam maksimal 80 baris berikutnya.
# Kita ambil penutup terakhir agar seluruh blok tanggal lama ikut terganti.
$end = -1
$max = [Math]::Min($lines.Count - 1, $start + 80)

for ($i = $start; $i -le $max; $i++) {
    if ($lines[$i].Trim() -eq "}") {
        $end = $i
    }
}

if ($end -lt 0) {
    throw "PENUTUP BLOK TANGGAL TIDAK DITEMUKAN"
}

$newBlock = @(
'            /*'
'             * FORMAT RESMI APLIKASI:'
'             * DD/MM/YYYY'
'             *'
'             * Contoh:'
'             * 05/10/2026 = 5 Oktober 2026'
'             */'
''
'            if ('
'                /^\d{2}\/\d{2}\/\d{4}$/.test(due)'
'            ) {'
''
'                /*'
'                 * Tanggal dari data yang sudah DD/MM/YYYY'
'                 * langsung digunakan.'
'                 */'
''
'                tanggalText.value ='
'                    due;'
''
'                return;'
''
'            }'
''
''
'            /*'
'             * FORMAT ISO:'
'             * YYYY-MM-DD'
'             *'
'             * Contoh:'
'             * 2026-10-05'
'             * menjadi:'
'             * 05/10/2026'
'             */'
''
'            if ('
'                /^\d{4}-\d{2}-\d{2}$/.test(due)'
'            ) {'
''
'                const parts ='
'                    due.split("-");'
''
'                tanggalText.value ='
'                    parts[2] +'
'                    "/" +'
'                    parts[1] +'
'                    "/" +'
'                    parts[0];'
''
'                return;'
''
'            }'
''
'        }'
)

$lines.RemoveRange(
    $start,
    ($end - $start + 1)
)

$lines.InsertRange($start, $newBlock)

# Simpan sebagai UTF-8
Set-Content $p $lines -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " OK - BLOK DUE DATE DIPERBAIKI"
Write-Host " FORMAT RESMI: DD/MM/YYYY"
Write-Host "=========================================="