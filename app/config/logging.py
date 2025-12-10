import logging
from rich.logging import RichHandler


def setup_logging():
    logging.basicConfig(format="%(message)s", level=logging.INFO, datefmt="[%X]", handlers=[RichHandler()])
