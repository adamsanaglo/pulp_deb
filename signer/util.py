import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("uvicorn")


def run_cmd_out(cmd: str) -> subprocess.CompletedProcess:
    """
    Run the specified command, returning the output of the command
    """
    res = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res.stdout = res.stdout.decode("utf-8", "replace")
    res.stderr = res.stderr.decode("utf-8", "replace")
    return res


def run_cmd(cmd: str) -> bool:
    """
    Run the specified command, returning True/False
    """
    res = run_cmd_out(cmd)
    if res.returncode != 0:
        log.warn(res.stderr)
        return False
    return True


def get_temporary_file(suffix: str = "") -> str:
    """
    Securely creates a temporary file and returns the corresponding filename
    """
    tmpfile = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    return tmpfile.name


def write_to_temporary_file(content: bytes, suffix: str = "") -> str:
    """
    Write the provided content to a temporary file,
    created securely via tempfile
    """
    tmpfile = get_temporary_file(suffix)
    with open(tmpfile, "wb") as f:
        f.write(content)
    return tmpfile


def create_working_dir(unsigned_file: tempfile.SpooledTemporaryFile, filename: str) -> str:
    temp_dir = tempfile.mkdtemp()
    with open(f"{temp_dir}/{filename}", 'wb') as f:
        f.write(unsigned_file.read())
    return temp_dir


def shred_working_dir(dir: Path) -> bool:
    """Securely delete files in the specified dir."""
    ret = True
    for file in dir.glob('*'):
        result = run_cmd(f"shred -uz {str(file)}")
        if not result:
            log.error(f"Could not shred file for some reason: {str(file)}")
        ret = ret and result
    dir.rmdir()
    return ret
