import asyncio
import re
import shlex
import subprocess
from collections import namedtuple
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, List, Optional

import aioshutil
from fastapi import UploadFile

from app.core.schemas import PackageType


class UnsupportedFiletype(Exception):
    pass


class PackageSignatureError(Exception):
    def __init__(
        self, msg: Optional[str] = None, filename: Optional[str] = None, error: Optional[str] = None
    ) -> None:
        if not msg:
            msg = "Package signature verification failed"
            if filename:
                msg += f" for {filename}"
            msg += ". Microsoft policy requires all packages to be signed by ESRP."
            if error:
                msg += " Specific error: " + error
        super().__init__(msg)


# Run at app startup to load keyring
keys_dir = Path(__file__).parent / "keys"
gpg_cmd = ["/usr/bin/gpg", "--no-default-keyring", "--keyring", str(keys_dir / ".keyring")]
rpm_cmd = ["/usr/bin/rpmkeys", "--dbpath", str(keys_dir)]
# There is also an "msopentech.asc" legacy key, but I'm ignoring it because:
# 1) Only legacy stuff is signed with it, no new things.
# 2) It fails to import into some versions of RPM for some unknown reason.
subprocess.run(gpg_cmd + ["--import", str(keys_dir / "microsoft.asc")], check=True)
subprocess.run(rpm_cmd + ["--import", str(keys_dir / "microsoft.asc")], check=True)
subprocess.run(rpm_cmd + ["--import", str(keys_dir / "mariner.asc")], check=True)


async def verify_signature(file: UploadFile, file_type: PackageType) -> None:
    if file_type == PackageType.rpm:
        await _verify_rpm_signature(file)
    elif file_type == PackageType.deb:
        await _verify_deb_signature(file)
    else:
        raise UnsupportedFiletype(
            f"We don't know how to verify the signature of this file: {file.filename}"
        )
    await file.seek(0)  # "reset" it to be read again


Result = namedtuple("Result", "returncode, stdout, stderr")


async def async_subprocess(cmd: List[str], **kwargs: Any) -> Result:
    """
    A simple async drop-in replacement for most subprocess.run functionality when shell=False.
    """
    # asyncio.subprocess doesn't escape args like subprocess.run does, do it ourselves.
    _cmd = [shlex.quote(x) for x in cmd]
    if "stdout" not in kwargs:
        kwargs["stdout"] = asyncio.subprocess.PIPE
    if "stderr" not in kwargs:
        kwargs["stderr"] = asyncio.subprocess.PIPE
    proc = await asyncio.subprocess.create_subprocess_exec(*_cmd, **kwargs)
    stdout_bytes, stderr_bytes = await proc.communicate()
    # asyncio.subprocess doesn't decode to strings, do it ourselves
    stdout = stdout_bytes.decode("utf-8") if stdout_bytes is not None else ""
    stderr = stderr_bytes.decode("utf-8") if stderr_bytes is not None else ""
    return Result(proc.returncode, stdout, stderr)


async def _verify_rpm_signature(file: UploadFile) -> None:
    """
    Call out to rpmkeys (which is what the signature-oriented options of "rpm" are aliases of)
    to ensure the rpm is signed by one of the keys in the keyring.
    """
    with NamedTemporaryFile() as f:
        await aioshutil.copyfileobj(file.file, f)
        f.flush()
        result = await async_subprocess(rpm_cmd + ["--verbose", "--checksig", f.name])
        stdout = result.stdout
        count = 0
        for match in re.finditer(r"Signature, key ID ([0-9a-fA-F]+): (OK|BAD|NOKEY)", stdout):
            count += 1
            if match.group(2) != "OK":
                raise PackageSignatureError(
                    filename=file.filename, error=f"Unrecognized key ID: {match.group(1)}"
                )
        if count == 0:
            raise PackageSignatureError(filename=file.filename, error="No signature detected!")
        if count != 2:  # Two because both the headers and the body should be signed.
            raise PackageSignatureError(filename=file.filename, error=f"Unknown Error: {stdout}")


async def _verify_deb_signature(file: UploadFile) -> None:
    """
    Here we recreate the check that "debsig-verify" would be doing.

    We are recreating it instead of just calling out to debsig-verify because debsig-verify is
    actually pretty complicated to set up correctly, and doing so would add a dependency that
    is not available on rpm-based systems (I don't know if that would ever really matter, but it's
    a consideration). This is just as good for our purposes.
    """
    with TemporaryDirectory() as td:
        dir = Path(td)
        # write the file to disk
        with (dir / "original").open("wb") as f:
            await aioshutil.copyfileobj(file.file, f)

        # unpack the archive
        res = await async_subprocess(["/usr/bin/ar", "x", "original"], cwd=td)
        if res.returncode != 0:
            raise PackageSignatureError(
                f"Failed to read package {file.filename}. Please check the package."
            )

        # cat the unpacked archive bits together
        with (dir / "combined").open("wb") as combined:
            for filename in ("debian-binary", "control.*", "data.*"):
                # There will only be one control.tar.gz (or whatever) file, but we have to glob
                # and iterate because the compression type can vary.
                for x in dir.glob(filename):
                    with x.open("rb") as f:
                        await aioshutil.copyfileobj(f, combined)

        # ask gpg if it's signed correctly
        result = await async_subprocess(gpg_cmd + ["--verify", "_gpgorigin", "combined"], cwd=td)
        if result.returncode != 0:
            raise PackageSignatureError(filename=file.filename)
