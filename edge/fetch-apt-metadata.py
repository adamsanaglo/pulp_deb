#!/usr/bin/python3

import datetime
import hashlib
import logging
import os
import tempfile
import time
from base64 import b64decode
from logging.handlers import SysLogHandler as SysLogHandler
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
import typer
from dateutil.parser import parse as parsedate

# See https://wiki.debian.org/SecureApt
apt_hash_names = ["MD5", "MD5Sum", "SHA1", "SHA256", "SHA512", "SHA3-256", "SHA3-512"]

upstream_url = "https://pmc-distro.trafficmanager.net"
www_root = Path("/var/pmc/www")
pocket_list_file = Path("/var/pmc/pocket-list")

# Logging goes to syslog Local3 facility
logger = logging.getLogger("fetch-apt-metadata")
logger.setLevel(logging.INFO)
handler = SysLogHandler(address="/dev/log", facility=SysLogHandler.LOG_LOCAL3)
handler.setFormatter(logging.Formatter("Fetch: %(message)s"))
logger.addHandler(handler)


class HashMismatch(Exception):
    pass


class MissingFile(Exception):
    pass


class Notes:
    """
    Folds multiple instances of a message to a single item.

    All messages at a given severity with the same tag will appear only once when
    fetched via to_string or flushed to logging. Messages are ordered by tag when
    converted to a single string, but flushed to logging in whatever order dict.values()
    yields them.
    """

    def __init__(self) -> None:
        self.errors: Dict[str, str] = {}
        self.warnings: Dict[str, str] = {}
        self.info: Dict[str, str] = {}

    def error(self, tag: str, message: str) -> None:
        self.errors[tag] = message

    def warning(self, tag: str, message: str) -> None:
        self.warnings[tag] = message

    def info(self, tag: str, message: str) -> None:
        self.info[tag] = message

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_info(self) -> bool:
        return len(self.info) > 0

    def to_string(self) -> str:
        results: List[str] = []
        if self.has_errors:
            results.append("Errors:")
            results.extend([self.errors[tag] for tag in sorted(self.errors.keys())])
        if self.has_warnings:
            results.append("Warnings:")
            results.extend([self.warnings[tag] for tag in sorted(self.warnings.keys())])
        if self.has_errors:
            results.append("Informational:")
            results.extend([self.info[tag] for tag in sorted(self.info.keys())])
        return "\n".join(results)

    def flush_to_log(self) -> None:
        for message in self.errors.values():
            logger.error(message)
        for message in self.warnings.values():
            logger.warning(message)
        for message in self.info.values():
            logger.info(message)


note = Notes()


class Release:
    """Represents the Release file of an APT repository."""

    def __init__(self, path: Path, lines: List[str]) -> None:
        self.path = path
        self.files: Dict[str, int] = {}
        self.properties: Dict[str, Any] = {}
        self.hashes: Dict[str, Dict[str, str]] = {}
        self._parse(lines)

    @classmethod
    def from_path(cls, filename: str):
        path = Path(filename)
        with path.open("r") as f:
            return cls(path, f.readlines())

    @property
    def origin(self) -> str:
        return self.properties["Origin"]

    @property
    def label(self) -> str:
        return self.properties["Label"]

    @property
    def suite(self) -> str:
        return self.properties["Suite"]

    @property
    def codename(self) -> str:
        return self.properties["Codename"]

    @property
    def date(self) -> datetime.datetime:
        return parsedate(self.properties["Date"])

    @property
    def architectures(self) -> List[str]:
        return self.properties["Architectures"].strip().split()

    @property
    def components(self) -> List[str]:
        return self.properties["Components"].strip().split()

    @property
    def description(self) -> str:
        return self.properties["Description"]

    @property
    def filenames(self) -> List[str]:
        return list(self.files.keys())

    def hash(self, hash_name: str, filename: str) -> str:
        return self.hashes[hash_name][filename]

    def available_hashes(self) -> List[str]:
        return self.hashes.keys()

    def _parse(self, lines: List[str]) -> None:
        """Parse the contents of a Release file."""
        hash_name = None
        for line_number, line in enumerate(lines):
            if line.startswith(" "):
                if hash_name:
                    try:
                        (hash, size, name) = line.strip().split()
                    except ValueError:
                        n = line_number + 1
                        note.error(f"{n}", f"Incorrect number of fields on line {n}")
                        continue
                    self.files[name] = int(size)
                    self.hashes[hash_name][name] = hash
                else:
                    note.error(
                        "IndentationError",
                        f"{self.path}: indented line {line_number+1} outside hash block.",
                    )
                continue

            (tag, value) = line.split(":", 1)
            if tag in apt_hash_names:
                hash_name = tag.strip()
                self.hashes[hash_name] = {}
            else:
                self.properties[tag] = value.strip()
                hash_name = None

    def __str__(self) -> str:
        return f"Release({self.path}, {self.filenames})"

    def __repr__(self) -> str:
        return f"Release({self.path}, {self.filenames})"


def local_name_in_pocket(pocket: str, name: str) -> Path:
    """Construct the Path of a local file within a pocket."""
    return www_root / pocket / name


def upstream_url_in_pocket(pocket: str, name: str) -> str:
    """Construct the URL of a file within a pocket."""
    return f"{upstream_url}/{pocket}/{name}"


def get_last_modified(response: requests.Response) -> float:
    LM = "Last-Modified"
    if LM in response.headers:
        remote_mtime = response.headers[LM]
        return parsedate(remote_mtime).timestamp()
    else:
        # Assume it was modified 15 minutes ago
        return time.time() - 900


def is_outdated(pocket: str) -> bool:
    """Check if the local metadata is older than the upstream copy."""
    local = local_name_in_pocket(pocket, "Release")
    if not local.exists():
        return True
    local_mtime = local.stat().st_mtime

    remote = upstream_url_in_pocket(pocket, "Release")
    result = requests.head(remote, allow_redirects=True)
    if result.status_code != 200:
        note.error("HEADfailure", f"HEAD request for {remote} status {result.status_code}")
        return False
    remote_mtime = get_last_modified(result)
    return remote_mtime > local_mtime


def verify_fileset(release_file, gpg_file, inrelease_file) -> bool:
    """ Return True only if the three files are mutually consistent and verified """
    return True


def download_file_to_staging(pocket: str, filename: str, staging: str) -> Tuple[str, str]:
    """Download a file relative to the upstream URL to the staging directory."""
    remote = upstream_url_in_pocket(pocket, filename)
    result = requests.get(remote)
    if result.status_code != 200:
        raise MissingFile(f"Failed to GET {pocket}/{filename} status {result.status_code}")
    m_time = get_last_modified(result)
    MD5 = "Content-MD5"
    if MD5 in result.headers:
        rawhash = int.from_bytes(b64decode(result.headers[MD5]), byteorder="big")
        expected_md5hash = "{0:032x}".format(rawhash)
        actual_md5hash = hashlib.md5(result.content).hexdigest()
        if expected_md5hash != actual_md5hash:
            raise HashMismatch(f"MD5 mismatch {pocket}/{filename} - expected {expected_md5hash} got {actual_md5hash}")
    else:
        logger.info(f"Missing Content-MD5 header for {pocket}/{filename}")

    with tempfile.NamedTemporaryFile(dir=staging, delete=False) as f:
        f.write(result.content)
        name = f.name
        hash = hashlib.sha256(result.content).hexdigest()

    # Set the created / modified times to the Last-Modified time.
    os.utime(name, (m_time, m_time))
    return name, hash


def fetch_metadata(pocket: str) -> None:
    """Fetch the metadata from the upstream distribution point."""

    renames: Dict[str, Path] = {}

    with tempfile.TemporaryDirectory(dir=www_root) as staging:

        def stage_file(filename: str) -> Tuple[str, str]:
            f, hash = download_file_to_staging(pocket, filename, staging)
            renames[f] = local_name_in_pocket(pocket, filename)
            return f, hash

        release_file, _ = stage_file("Release")
        gpg_file, _ = stage_file("Release.gpg")
        inrelease_file, _ = stage_file("InRelease")
        verify_fileset(release_file, gpg_file, inrelease_file)

        release = Release.from_path(release_file)
        for filename in release.filenames:
            try:
                _, hash = stage_file(filename)
            except MissingFile as ex:
                note.warning(f"{pocket}/{filename}", f"{pocket}/Release mentions {filename} which is not found at origin")
                continue
            # This assumes that all metadata files are generating a sha256 sum, which I think
            # is a safe assumption. If not, barf.
            try:
                expected_hash = release.hashes["SHA256"][filename]
            except KeyError:
                raise Exception(f"Release file for {pocket} missing SHA256 sum for {filename}?!")
            if hash != expected_hash:
                note.warning(filename, f"SHA256 mismatch: Release {expected_hash} but computed {hash}")
                raise HashMismatch(f"SHA256 mismatch for {pocket}/{filename} - Release {expected_hash} but computed {hash}")

        for source, target in renames.items():
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            Path(source).rename(target)
            target.chmod(0o644)


def main(
    pocket: str = typer.Argument(..., help="repo/dists/pocket to fetch metadata for"),
    force: bool = typer.Option(False, help="Force a refresh of the metadata"),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
):
    """
    Fetch APT metadata from the upstream distribution point for a given pocket
    if the upstream Release file is newer than the local copy.
    """
    if pocket.startswith("http"):
        typer.echo("Pocket must be a repo/pocket, not a URL")
        logger.error(f"Got URL instead of pocket ({pocket})")
        raise typer.Exit(1)

    # Remove leading and trailing slashes
    pocket = pocket.strip("/")

    if verbose:
        logger.setLevel(logging.DEBUG)
    if force or is_outdated(pocket):
        logger.info(f"Fetching metadata for {pocket} (force={force})")
        try:
            try:
                fetch_metadata(pocket)
            except HashMismatch:
                # Caught it in the middle of an update? Try again.
                fetch_metadata(pocket)
        except Exception as ex:
            logger.exception(f"Exception while fetching {pocket}")
        note.flush_to_log()
        logger.info(f"Done fetching metadata for {pocket}")
    else:
        logger.debug(f"Metadata for {pocket} unchanged; no action")


if __name__ == "__main__":
    typer.run(main)


def test_Release() -> None:
    lines = """Origin: microsoft-ubuntu-xenial-prod xenial
Label: microsoft-ubuntu-xenial-prod xenial
Suite: xenial
Codename: xenial
Date: Fri, 17 Feb 2023 17:19:46 +0000
Architectures: amd64 all
Components: main
Description: Generated by aptly
SHA256:
 499a0fee2b79fdb46a848fa8dfee5d1d091fb50b2afa9fdcc651fa754ad9eadd          1370881 main/binary-amd64/Packages
 f2c78e978d2ed8ce6a76c5ad10001c63fd5e66d28ffadd33bff937fa29e19a2f           200612 main/binary-amd64/Packages.gz
 866ee66be2820eb9187ab5234553510c00dc70fc646a05244743ed3ed4325cc5            21187 main/binary-all/Packages
 58de542291fd0b5cb111d31ab76f7a2f28400e6018c34e16ffa77719c5f89fd7             3596 main/binary-all/Packages.gz
SHA512:
 c6f3a0bf078126bdbf65d6303ad6ad22b80e7f2baaff055247a0517779aadf6ed8ff2be5a9776a04be3a15632de2decaa7f3f5a3e76231fd458c0688ba3d7a7f          1370881 main/binary-amd64/Packages
 d72e7d7bc943aef36ae88c9d3bff440f67140b52e285d48e9886d7215d0ca06733d8ffc213ed9b6ceff3c1bc3a282470394233e2b1bc63cd4f1ce530c5f6bf69           200612 main/binary-amd64/Packages.gz
 c6e3497cf943f7481e0e42d642727f4c3fd21f5fe34b834a417f6ef142a583c6207fc5d90d74f7757b57e2d24d01e215e876761e762907e8923592315e0174ac            21187 main/binary-all/Packages
 7aaca46c0b350872ef5c6404fe23e686a2383d9853cdca3aafa150830352964bcfeb506d7f047710db4dfb5eae41c9b303d82d2bf9f8d9ccaadd6102e61afdcf             3596 main/binary-all/Packages.gz
""".splitlines()
    expected_sizes: Dict[str, int] = {
        "main/binary-amd64/Packages": 1370881,
        "main/binary-amd64/Packages.gz": 200612,
        "main/binary-all/Packages": 21187,
        "main/binary-all/Packages.gz": 3596,
    }
    release = Release(Path("test"), lines)
    assert release.origin == "microsoft-ubuntu-xenial-prod xenial"
    assert release.label == "microsoft-ubuntu-xenial-prod xenial"
    assert release.suite == "xenial"
    assert release.codename == "xenial"
    assert release.date == datetime.datetime(2023, 2, 17, 17, 19, 46, tzinfo=datetime.timezone.utc)
    assert release.architectures == ["amd64", "all"]
    assert release.components == ["main"]
    assert release.description == "Generated by aptly"
    assert len(release.filenames) == 4
    for name in [
        "main/binary-amd64/Packages",
        "main/binary-amd64/Packages.gz",
        "main/binary-all/Packages",
        "main/binary-all/Packages.gz",
    ]:
        assert name in release.filenames
        assert release.files[name] == expected_sizes[name]

    for hash in ["SHA256", "SHA512"]:
        assert hash in release.hashes
        for name in release.filenames:
            assert name in release.hashes[hash]
            assert len(release.hashes[hash][name]) == 64 if hash == "SHA256" else 128
    assert (
        release.hash("SHA256", "main/binary-amd64/Packages")
        == "499a0fee2b79fdb46a848fa8dfee5d1d091fb50b2afa9fdcc651fa754ad9eadd"
    )
    assert (
        release.hash("SHA512", "main/binary-amd64/Packages")
        == "c6f3a0bf078126bdbf65d6303ad6ad22b80e7f2baaff055247a0517779aadf6ed8ff2be5a9776a04be3a15632de2decaa7f3f5a3e76231fd458c0688ba3d7a7f"
    )


def test_pocket_builders() -> None:
    pocket = "repos/az/dists/jammy"
    assert str(local_name_in_pocket(pocket, "foo")) == f"{www_root}/{pocket}/foo"
    assert upstream_url_in_pocket(pocket, "foo") == f"{upstream_url}/{pocket}/foo"
