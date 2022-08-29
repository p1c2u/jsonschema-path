from typing import TYPE_CHECKING

from openapi_spec.handlers.file import FileHandler

if TYPE_CHECKING:
    from openapi_spec.handlers.requests import UrlRequestsHandler as UrlHandler
else:
    try:
        from openapi_spec.handlers.requests import (
            UrlRequestsHandler as UrlHandler,
        )
    except ImportError:
        from openapi_spec.handlers.urllib import UrllibHandler as UrlHandler

__all__ = ["FileHandler", "UrlHandler"]

file_handler = FileHandler()
all_urls_handler = UrlHandler("http", "https", "file")
default_handlers = {
    "<all_urls>": all_urls_handler,
    "http": UrlHandler("http"),
    "https": UrlHandler("https"),
    "file": UrlHandler("file"),
}
