$p = "templates\pelanggan_tambah.html"

$s = Get-Content $p -Raw

$startMarker = @'
        // ==========================
        // DUE DATE
        // ==========================
'@

$endMarker = @'
        // ==========================
'@

$start = $s.IndexOf($startMarker)

if ($start -lt 0) {
    throw "BLOK DUE DATE TIDAK DITEMUKAN"
}

$afterStart = $start + $startMarker.Length

$end = $s.IndexOf($endMarker, $afterStart)

if ($end -lt 0) {
    throw "AKHIR BLOK DUE DATE TIDAK DITEMUKAN"
}

$newBlock = @'
        // ==========================
        // DUE DATE
        // ==========================

        match =
            comment.match(
                /(?:^|;)due:([^;]*)/i
            );

        if (
            match &&
            match[1].trim()
        ) {

            let due =
                match[1].trim();


            /*
             * FORMAT RESMI APLIKASI:
             * DD/MM/YYYY
             *
             * Contoh:
             * 05/10/2026
             *
             * Artinya:
             * 5 Oktober 2026
             */

            if (
                /^\d{2}\/\d{2}\/\d{4}$/.test(due)
            ) {

                /*
                 * Data sudah menggunakan
                 * format DD/MM/YYYY.
                 */

                tanggalText.value =
                    due;

                return;

            }


            /*
             * FORMAT ISO:
             * YYYY-MM-DD
             *
             * Contoh:
             * 2026-10-05
             *
             * Diubah menjadi:
             * 05/10/2026
             */

            if (
                /^\d{4}-\d{2}-\d{2}$/.test(due)
            ) {

                const parts =
                    due.split("-");

                tanggalText.value =
                    parts[2] +
                    "/" +
                    parts[1] +
                    "/" +
                    parts[0];

                return;

            }

        }


'@

$s = $s.Substring(0, $start) +
     $newBlock +
     $s.Substring($end)

Set-Content $p $s -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " OK - DUE DATE DIPERBAIKI"
Write-Host " FORMAT RESMI: DD/MM/YYYY"
Write-Host " KODE LAIN TIDAK DIUBAH"
Write-Host "=========================================="