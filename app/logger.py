import logging
from logging.handlers import TimedRotatingFileHandler
import os

logger = logging.getLogger("audit_logger")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(
    "logs/audit.log",
    when="midnight",
    interval=1,
    backupCount=30
)

handler.suffix = "%Y-%m-%d"

# 🔥 Custom filename format
def custom_namer(default_name):
    # default_name = logs/audit.log.2026-05-05
    base_dir, filename = os.path.split(default_name)
    name, date = filename.rsplit(".", 1)  # split at last dot

    base_name = name.replace(".log", "")  # remove .log
    new_filename = f"{base_name}.{date}.log"

    return os.path.join(base_dir, new_filename)

handler.namer = custom_namer

formatter = logging.Formatter("%(asctime)s | %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)