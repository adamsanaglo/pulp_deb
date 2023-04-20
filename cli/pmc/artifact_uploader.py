import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from click import BadParameter
from pydantic import AnyHttpUrl, ValidationError, parse_obj_as

from pmc.client import client, init_session, session_context
from pmc.context import PMCContext
from pmc.utils import PulpTaskFailure

SHA256_REGEX = r"?P<sha256>[a-fA-F0-9]{64}"
ARTIFACT_EXISTS_ERROR = rf"Artifact with sha256 checksum of '{SHA256_REGEX}' already exists."


class ArtifactUploader:
    def __init__(
        self,
        context: PMCContext,
        path_or_url: str,
    ):
        self.context = context

        try:
            self.url = parse_obj_as(AnyHttpUrl, path_or_url)
        except ValidationError:
            self.url = None
            self.path = Path(path_or_url)
            if not self.path.is_file() and not self.path.is_dir():
                raise BadParameter(
                    f"Invalid url or non-existent file/directory for artifact {self.path}."
                )

    def _build_data(self) -> Dict[str, Any]:
        """Build data dict for uploading artifact(s)."""
        data: Dict[str, Any] = {}

        if self.url:
            data["url"] = self.url

        return data

    def _find_existing_artifact(self, error_resp: Any) -> Any:
        """Attempt to find the existing artifact if it exists"""
        error = error_resp.get("detail")

        if match := re.search(ARTIFACT_EXISTS_ERROR, error["non_field_errors"]):
            resp = client.get("/artifacts/", params=match.groupdict())
            results = resp.json()["results"]
            if len(results) == 1:
                return results[0]

        raise KeyError()

    def _upload_artifact(self, data: Dict[str, Any], path: Optional[Path] = None) -> Any:
        if path:
            files = {"file": path.open("rb")}
        else:
            files = None

        # upload the artifact
        resp = client.post("/artifacts/", params=data, files=files)
        resp_json = resp.json()

        if not resp.ok:
            try:
                return self._find_existing_artifact(resp)
            except KeyError:
                # we're not dealing with a failure due to an existing artifact
                raise PulpTaskFailure(
                    {
                        "error": {
                            "traceback": resp_json["command_traceback"],
                            "description": resp_json["message"],
                        }
                    }
                )

        return resp_json

    def _upload_artifacts(
        self, data: Dict[str, Any], paths: Iterable[Path] = []
    ) -> List[Dict[str, Any]]:
        def set_context(context: PMCContext) -> None:
            session_context.set(init_session(context))

        artifacts = []
        with ThreadPoolExecutor(
            max_workers=5, initializer=set_context, initargs=(self.context,)
        ) as executor:
            futures = [executor.submit(self._upload_artifact, data, path) for path in paths]
            for future in as_completed(futures):
                artifacts.append(future.result())

        return artifacts

    def upload(self) -> List[Dict[str, Any]]:
        """Perform the upload."""
        data = self._build_data()

        if self.url:
            return [self._upload_artifact(data)]
        elif self.path.is_dir():
            return self._upload_artifacts(data, self.path.glob("*"))
        else:
            return [self._upload_artifact(data, self.path)]
