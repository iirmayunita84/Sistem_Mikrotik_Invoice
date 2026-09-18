import traceback
from datetime import datetime

LOG_FILE = "error.log"

def log_error(where, error):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write(f"WAKTU : {datetime.now()}\n")
        f.write(f"LOKASI: {where}\n")
        f.write(f"ERROR : {str(error)}\n")
        f.write("TRACE:\n")
        f.write(traceback.format_exc())
        f.write("\n\n")