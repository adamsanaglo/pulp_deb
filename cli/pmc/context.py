import sys
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .auth import pmcauth
from .schemas import Config


class PMCContext:
    def __init__(self, config: Config, config_path: Optional[Path] = None):
        self.cid = uuid4()
        self.config = config
        self.config_path = config_path
        self.isatty = sys.stdout.isatty()
        self.auth = pmcauth(**self.config.auth_fields())

    def __getattr__(self, key: str) -> Any:
        try:
            return self.config.dict()[key]
        except ValueError:
            raise AttributeError(f"PMCContext has not attribute '{key}'.")
