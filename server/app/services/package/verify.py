import shutil
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Optional

from fastapi import UploadFile


class UnsupportedFiletype(Exception):
    pass


class UnsignedPackage(Exception):
    def __init__(self, msg: Optional[str] = None) -> None:
        if not msg:
            msg = "Microsoft policy requires all packages to be signed by ESRP."
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


async def verify_signature(file: UploadFile) -> None:
    if file.filename.endswith(".rpm"):
        _verify_rpm_signature(file)
    elif file.filename.endswith(".deb"):
        _verify_deb_signature(file)
    else:
        raise UnsupportedFiletype(
            "We don't know how to verify the signature of this file: " + file.filename
        )
    await file.seek(0)  # "reset" it to be read again


def _verify_rpm_signature(file: UploadFile) -> None:
    """
    Call out to rpmkeys (which is what the signature-oriented options of "rpm" are aliases of)
    to ensure the rpm is signed by one of the keys in gpg's keyring.
    """
    with NamedTemporaryFile() as f:
        shutil.copyfileobj(file.file, f)
        result = subprocess.run(rpm_cmd + ["--checksig", f.name])
        if result.returncode != 0:
            raise UnsignedPackage


def _verify_deb_signature(file: UploadFile) -> None:
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
            shutil.copyfileobj(file.file, f)

        # unpack the archive
        subprocess.run(["/usr/bin/ar", "x", "original"], cwd=td, check=True)

        # cat the unpacked archive bits together
        with (dir / "combined").open("wb") as combined:
            for filename in ("debian-binary", "control.*", "data.*"):
                # There will only be one control.tar.gz (or whatever) file, but we have to glob
                # and iterate because the compression type can vary.
                for x in dir.glob(filename):
                    with x.open("rb") as f:
                        combined.write(f.read())

        # ask gpg if it's signed correctly
        result = subprocess.run(gpg_cmd + ["--verify", "_gpgorigin", "combined"], cwd=td)
        if result.returncode != 0:
            raise UnsignedPackage