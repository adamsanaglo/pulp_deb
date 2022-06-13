from uuid import uuid4
import sys
from pathlib import Path
from typing import Optional

from .schemas import Config


class PMCContext:
    def __init__(self, config: Config, config_path: Optional[Path] = None):
        self.cid = uuid4()
        self.config = config
        self.config_path = config_path
        self.isatty = sys.stdout.isatty()
