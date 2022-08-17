import subprocess
import logging
import tempfile

from pathlib import Path
from typing import List

log = logging.getLogger('uvicorn')


def run_cmd(cmd_split: List[str]) -> bool:
    """
    Run the specified command, returning True/False
    """
    res = subprocess.run(cmd_split, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res.stdout = res.stdout.decode('utf-8', 'replace')
    res.stderr = res.stderr.decode('utf-8', 'replace')
    if res.returncode != 0:
        log.warn(res.stderr)
        return False
    return True


def get_temporary_file(suffix: str = '') -> str:
    """
    Securely creates a temporary file and returns the corresponding filename
    """
    tmpfile = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    return tmpfile.name


def write_to_temporary_file(content: bytes, suffix: str = '') -> str:
    """
    Write the provided content to a temporary file,
    created securely via tempfile
    """
    tmpfile = get_temporary_file(suffix)
    with open(tmpfile, 'wb') as f:
        f.write(content)
    return tmpfile


def secure_delete(filename: str) -> bool:
    """
    Securely delete the specified file
    """
    if not Path(filename).is_file():
        log.error(f'Cannot securely delete {filename}. It is not a file.')
        return False
    cmd_split = ['shred', '-uz', filename]
    return run_cmd(cmd_split)
