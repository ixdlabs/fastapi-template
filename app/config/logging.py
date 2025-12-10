import logging
from rich.logging import RichHandler


def setup_logging():
    logging.basicConfig(format="%(message)s", level=logging.INFO, datefmt="[%X]", handlers=[RichHandler()])
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").propagate = False
