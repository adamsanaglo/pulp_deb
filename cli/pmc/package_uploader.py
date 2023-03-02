from pathlib import Path
from typing import Any, Dict, List, Optional

from click import BadParameter
from pydantic import AnyHttpUrl, ValidationError, parse_obj_as

from pmc.client import client, poll_task
from pmc.context import PMCContext
from pmc.schemas import PackageType
from pmc.utils import raise_if_task_failed


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

    def _package_upload(self, data: Dict[str, Any], path: Optional[Path] = None) -> Any:
        if path:
            files = {"file": open(path, "rb")}
        else:
            files = None

        # upload and poll the task
        resp = client.post("/packages/", params=data, files=files)
        task_resp = poll_task(resp.json().get("task"))
        task = task_resp.json()
        raise_if_task_failed(task)

        # grab the package json
        package_id = task["created_resources"][0]
        package_resp = client.get(f"/packages/{package_id}/")
        return package_resp.json()

    def upload(self) -> List[Dict[str, Any]]:
        """Perform the upload."""
        data = self._build_data()
        packages = []

        if self.url:
            package = self._package_upload(data)
            return [package]

        if self.path.is_dir():
            # handle directory
            for pkg in self.path.glob("*"):
                packages.append(self._package_upload(data, pkg))
        else:
            packages = [self._package_upload(data, self.path)]

        return packages
