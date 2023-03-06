import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from click import BadParameter
from pydantic import AnyHttpUrl, ValidationError, parse_obj_as

from pmc.client import client, client_context, create_client, poll_task
from pmc.context import PMCContext
from pmc.schemas import PackageType
from pmc.utils import PulpTaskFailure, raise_if_task_failed

SHA256_REGEX = r"?P<sha256>[a-fA-F0-9]{64}"
PACKAGE_EXISTS_ERRORS = {
    PackageType.file: (
        r"There is already a file content with relative path '(?P<relative_path>\S+?)' "
        rf"and digest '({SHA256_REGEX})'"
    ),
    PackageType.deb: (
        r"There is already a deb package with relative path '(?P<relative_path>\S+?)' "
        rf"and sha256 '({SHA256_REGEX})'"
    ),
    PackageType.rpm: (
        r"There is already a package with: arch=(?P<arch>\S+?), checksum_type=sha256, "
        rf"epoch=(?P<epoch>\S+?), name=(?P<name>\S+?), pkgId=({SHA256_REGEX}), "
        r"release=(?P<release>\S+?), version=(?P<version>\S+)\."
    ),
}


class PackageUploader:
    def __init__(
        self,
        context: PMCContext,
        path_or_url: str,
        ignore_signature: Optional[bool] = False,
        file_type: Optional[PackageType] = None,
        relative_path: Optional[str] = None,
    ):
        self.ignore_signature = ignore_signature
        self.file_type = file_type
        self.relative_path = relative_path
        self.context = context

        try:
            self.url = parse_obj_as(AnyHttpUrl, path_or_url)
        except ValidationError:
            self.url = None
            try:
                self.path = Path(path_or_url)
            except FileNotFoundError:
                raise BadParameter("Invalid path/url for package.")

            if self.path.is_dir():
                if self.relative_path:
                    raise BadParameter("Cannot supply relative path with directory of packages.")

    def _build_data(self) -> Dict[str, Any]:
        """Build data dict for uploading package(s)."""
        data: Dict[str, Any] = {
            "ignore_signature": self.ignore_signature,
        }

        if self.url:
            data["url"] = self.url
        if self.file_type:
            data["file_type"] = self.file_type
        if self.relative_path:
            data["relative_path"] = self.relative_path

        return data

    def _find_existing_package(self, task: Any) -> Any:
        """Attempt to find the existing package if it exists"""
        # TODO: handle python packages. Unlike the other package types, the python package error
        # message doesn't return uniquely identifying information. But we should be able to get the
        # sha256 digest from the package and look it up in the api.
        error = task.get("error")

        for package_type, err_search in PACKAGE_EXISTS_ERRORS.items():
            if match := re.search(err_search, error["description"]):
                resp = client.get(f"/{package_type}/packages/", params=match.groupdict())
                results = resp.json()["results"]
                if len(results) == 1:
                    return results[0]

        return False

    def _upload_package(self, data: Dict[str, Any], path: Optional[Path] = None) -> Any:
        if path:
            files = {"file": open(path, "rb")}
        else:
            files = None

        # upload and poll the task
        resp = client.post("/packages/", params=data, files=files)
        task_resp = poll_task(resp.json().get("task"))
        task = task_resp.json()

        try:
            raise_if_task_failed(task)
        except PulpTaskFailure:
            package = self._find_existing_package(task)
            if not package:
                # we're not dealing with a failure due to an existing package
                raise
            return package

        # grab the package json
        package_id = task["created_resources"][0]
        package_resp = client.get(f"/packages/{package_id}/")
        return package_resp.json()

    def _upload_packages(
        self, data: Dict[str, Any], paths: Iterable[Path] = []
    ) -> List[Dict[str, Any]]:
        def set_context(context: PMCContext) -> None:
            client_context.set(create_client(context))

        packages = []
        with ThreadPoolExecutor(
            max_workers=5, initializer=set_context, initargs=(self.context,)
        ) as executor:
            futures = [executor.submit(self._upload_package, data, path) for path in paths]
            for future in as_completed(futures):
                packages.append(future.result())
        return packages

    def upload(self) -> List[Dict[str, Any]]:
        """Perform the upload."""
        data = self._build_data()

        if self.url:
            return [self._upload_package(data)]
        elif self.path.is_dir():
            return self._upload_packages(data, self.path.glob("*"))
        else:
            return [self._upload_package(data, self.path)]
