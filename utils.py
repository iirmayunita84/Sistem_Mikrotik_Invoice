from core.logic import cek_demo, is_user_premium


def get_transaksi_list():
    data = get_pelanggan_list()

    transaksi = [
        p for p in data
        if p.get("status") in ("Lunas", "Aktif")
        and p.get("tanggal_bayar")
    ]

    transaksi.sort(
        key=lambda x: x["tanggal_bayar"],
        reverse=True
    )

    return transaksi

def boleh_masuk(user_id):
    """
    Return:
    (ok, mode, sisa_hari)
    ok   : True / False
    mode : 'TRIAL' | 'PREMIUM' | 'EXPIRED'
    """
    # Premium selalu boleh
    if is_user_premium(user_id):
        return True, "PREMIUM", 0

    # Cek demo / trial
    aktif, sisa = cek_demo(user_id)
    if aktif:
        return True, "TRIAL", sisa

    return False, "EXPIRED", 0