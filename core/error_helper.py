import logging
import uuid
from datetime import datetime


logger = logging.getLogger("app_logger")


def log_error(source, error):

    error_id = (
        f"ERR-{datetime.now():%Y%m%d}-"
        f"{uuid.uuid4().hex[:6].upper()}"
    )

    logger.exception(
        f"""
ERROR_ID : {error_id}
SOURCE   : {source}
ERROR    : {error}
"""
    )

    return error_id