$p = "templates\pelanggan_tambah.html"

# Backup kondisi sekarang
Copy-Item $p "$p.sebelum_format_ddmmyyyy.bak" -Force

$s = Get-Content $p -Raw

$startMarker = @'
    // =====================================================
    // FORMAT TANGGAL
'@

$endMarker = @'
    // =====================================================
    // VALIDASI SAAT FORM SUBMIT
'@

$start = $s.IndexOf($startMarker)
$end = $s.IndexOf($endMarker)

if ($start -lt 0) {
    throw "AWAL BLOK FORMAT TANGGAL TIDAK DITEMUKAN"
}

if ($end -lt 0) {
    throw "AKHIR BLOK FORMAT TANGGAL TIDAK DITEMUKAN"
}

if ($end -le $start) {
    throw "POSISI BLOK TANGGAL TIDAK VALID"
}

$newBlock = @'
    // =====================================================
    // FORMAT TANGGAL
    // FORMAT RESMI APLIKASI:
    // DD/MM/YYYY
    // =====================================================

    function formatTanggalInput(value) {

        if (!value) {
            return "";
        }

        // Hapus karakter selain angka
        let angka =
            value.replace(/\D/g, "");

        // Maksimal 8 angka
        angka =
            angka.substring(0, 8);

        // DD/MM/YYYY
        if (angka.length <= 2) {

            return angka;

        }

        if (angka.length <= 4) {

            return (
                angka.substring(0, 2) +
                "/" +
                angka.substring(2)
            );

        }

        return (
            angka.substring(0, 2) +
            "/" +
            angka.substring(2, 4) +
            "/" +
            angka.substring(4, 8)
        );

    }


    // =====================================================
    // VALIDASI DD/MM/YYYY
    // =====================================================

    function tanggalValid(value) {

        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            return false;
        }

        const parts =
            value.split("/");

        const day =
            parseInt(parts[0], 10);

        const month =
            parseInt(parts[1], 10);

        const year =
            parseInt(parts[2], 10);

        if (
            month < 1 ||
            month > 12 ||
            day < 1 ||
            day > 31
        ) {
            return false;
        }

        const d =
            new Date(
                year,
                month - 1,
                day
            );

        return (
            d.getFullYear() === year &&
            d.getMonth() === month - 1 &&
            d.getDate() === day
        );

    }


    // =====================================================
    // INPUT MANUAL
    //
    // Contoh:
    // 05102026
    //
    // menjadi:
    // 05/10/2026
    // =====================================================

    tanggalText.addEventListener(
        "input",
        function () {

            this.value =
                formatTanggalInput(
                    this.value
                );

        }
    );


    // =====================================================
    // KALENDER
    //
    // Aplikasi : DD/MM/YYYY
    // Browser   : YYYY-MM-DD
    // =====================================================

    btnKalender.addEventListener(
        "click",
        function () {

            const value =
                tanggalText.value.trim();

            /*
             * Contoh:
             *
             * DD/MM/YYYY
             * 05/10/2026
             *
             * menjadi:
             *
             * YYYY-MM-DD
             * 2026-10-05
             */

            if (
                /^\d{2}\/\d{2}\/\d{4}$/.test(value)
            ) {

                const parts =
                    value.split("/");

                const day =
                    parts[0];

                const month =
                    parts[1];

                const year =
                    parts[2];

                kalender.value =
                    year +
                    "-" +
                    month +
                    "-" +
                    day;

            }

            /*
             * Buka kalender browser.
             */

            if (
                typeof kalender.showPicker === "function"
            ) {

                kalender.showPicker();

            } else {

                kalender.focus();
                kalender.click();

            }

        }
    );


    // =====================================================
    // SAAT TANGGAL DIPILIH DARI KALENDER
    //
    // Browser:
    // YYYY-MM-DD
    //
    // Aplikasi:
    // DD/MM/YYYY
    // =====================================================

    kalender.addEventListener(
        "change",
        function () {

            if (!this.value) {
                return;
            }

            const parts =
                this.value.split("-");

            if (parts.length !== 3) {
                return;
            }

            const year =
                parts[0];

            const month =
                parts[1];

            const day =
                parts[2];

            tanggalText.value =
                day +
                "/" +
                month +
                "/" +
                year;

        }
    );


'@

$s = $s.Substring(0, $start) +
     $newBlock +
     $s.Substring($end)

Set-Content $p $s -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " OK - FORMAT TANGGAL DIPERBAIKI"
Write-Host " FORMAT RESMI: DD/MM/YYYY"
Write-Host " 05/10/2026 = 5 OKTOBER 2026"
Write-Host " KODE SUBMIT DAN DHCP TIDAK DIUBAH"
Write-Host "=========================================="