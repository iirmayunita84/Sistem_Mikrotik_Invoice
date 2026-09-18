from pathlib import Path

path = Path(r"templates\pelanggan_edit.html")
text = path.read_text(encoding="utf-8")

start = text.find("        function formatTanggal(tanggal) {")
end = text.find("        const nilaiAwal =", start)

if start == -1:
    raise SystemExit("ERROR: function formatTanggal tidak ditemukan.")

if end == -1:
    raise SystemExit("ERROR: const nilaiAwal tidak ditemukan.")

new_block = r'''        // ==================================================
        // KONVERSI TANGGAL
        //
        // FORMAT APLIKASI:
        // DD/MM/YYYY
        //
        // Contoh:
        // 05/10/2026 = 5 Oktober 2026
        // ==================================================

        function formatTanggal(tanggal) {

            if (!tanggal) {
                return "";
            }

            tanggal = String(tanggal).trim();

            // Database: DD/MM/YYYY
            if (/^\d{2}\/\d{2}\/\d{4}$/.test(tanggal)) {
                return tanggal;
            }

            // Kalender browser: YYYY-MM-DD
            if (/^\d{4}-\d{2}-\d{2}$/.test(tanggal)) {

                const bagian = tanggal.split("-");

                return (
                    bagian[2] +
                    "/" +
                    bagian[1] +
                    "/" +
                    bagian[0]
                );
            }

            return "";
        }


        // ==================================================
        // DD/MM/YYYY
        // MENJADI YYYY-MM-DD
        // UNTUK KALENDER BROWSER
        // ==================================================

        function tanggalUntukKalender(tanggal) {

            if (!tanggal) {
                return "";
            }

            const cocok =
                String(tanggal)
                    .trim()
                    .match(
                        /^(\d{2})\/(\d{2})\/(\d{4})$/
                    );

            if (!cocok) {
                return "";
            }

            const hari = cocok[1];
            const bulan = cocok[2];
            const tahun = cocok[3];

            return (
                tahun +
                "-" +
                bulan +
                "-" +
                hari
            );
        }


        // ==================================================
        // YYYY-MM-DD
        // MENJADI DD/MM/YYYY
        // ==================================================

        function dariKalender(tanggal) {

            if (!tanggal) {
                return "";
            }

            const bagian = tanggal.split("-");

            if (bagian.length !== 3) {
                return "";
            }

            return (
                bagian[2] +
                "/" +
                bagian[1] +
                "/" +
                bagian[0]
            );
        }


        // ==================================================
        // NORMALISASI NILAI SAAT HALAMAN DIBUKA
        // ==================================================

'''

path.write_text(
    text[:start] + new_block + text[end:],
    encoding="utf-8"
)

print("OK: blok konversi tanggal berhasil diperbaiki.")