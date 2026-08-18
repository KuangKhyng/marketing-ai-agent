"""
Cấu hình logging cho toàn app.

Trước đây codebase không có một dòng logging nào, mà lại có ~22 chỗ
`except Exception` trong đó nhiều chỗ `pass` im lặng. Trên Railway khi cache
hoặc persist session hỏng thì không có cách nào biết.

Nguyên tắc:
  - Module chỉ làm `logger = logging.getLogger(__name__)`, không tự cấu hình.
  - Entrypoint (api/main.py, cli.py) gọi setup_logging() một lần.
  - LOG_LEVEL đọc từ env, mặc định INFO.
"""
import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"

_configured = False


def setup_logging(level: str | None = None) -> None:
    """Gọi một lần ở entrypoint. Gọi nhiều lần cũng không nhân đôi handler."""
    global _configured
    if _configured:
        return

    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))

    root = logging.getLogger()
    root.setLevel(getattr(logging, resolved, logging.INFO))
    root.addHandler(handler)

    # httpx log mọi request lên Anthropic ở INFO — ồn, không có giá trị
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True
