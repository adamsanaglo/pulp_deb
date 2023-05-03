import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException

from app.core.schemas import (
    PackageId,
    PackageType,
    ReleaseId,
    RepoId,
    StrictDebPackageQuery,
    StrictDebSourcePackageQuery,
    StrictFilePackageQuery,
    StrictPythonPackageQuery,
    StrictRpmPackageQuery,
)
from app.services.pulp.api import PackageApi, ReleaseApi, RepositoryApi
from app.services.pulp.utils import yield_all

logger = logging.getLogger(__name__)


async def package_lookup(
    repo: RepoId,
    package_type: PackageType,
    release: Union[str, ReleaseId, None] = None,
    package_ids: Optional[List[PackageId]] = None,
    package_queries: Optional[
        List[
            Union[
                StrictDebPackageQuery,
                StrictDebSourcePackageQuery,
                StrictRpmPackageQuery,
                StrictPythonPackageQuery,
                StrictFilePackageQuery,
            ]
        ]
    ] = None,
) -> List[Dict[str, Any]]:
    """
    Look up packages in a repo as efficiently as possible. If neither package_ids nor
    package_queries is provided then will return all packages in the repo/release.
    WARNING: looking up less than 10 packages by ID does *NOT* guarantee that they're actually in
    the repo!
    This method returns *all* the packages (not a page) so it is only useful internally.
    """
    # If the list of packages is large enough we can list all packages in the repo and match them.
    # How large "large enough" is depends on how many packages are in the repo, and what percentage
    # of them we're deleting, and how much overhead there is dealing with multiple requests instead
    # of cursors and pages and whatever, so let's pick a number and say "10" is large enough.

    if package_queries is None:
        package_queries = []
    if package_ids is None:
        package_ids = []

    request_size = len(package_queries + package_ids)
    params = {}
    ret = []
    # Let's only bother loading the id, filename, and identifying fields of the package here.
    params["fields"] = ",".join(
        package_type.natural_key_fields + ["pulp_href", package_type.pulp_filename_field]
    )
    if release:
        # Release package filter assumes latest version, don't have to look it up.
        params["repository"] = repo
        if isinstance(release, ReleaseId):
            params["release"] = release
        else:
            try:
                rel = await ReleaseApi.get_repo_release(repo, release)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            params["release"] = ReleaseId(rel["id"])
    else:
        # Look up the current repo version once so we don't have to do it for each page.
        params["repository_version"] = await RepositoryApi.latest_version(repo)

    if request_size < 10 and request_size > 0:
        # Do individual lookups.
        for thing in package_queries + package_ids:
            if isinstance(thing, PackageId):
                # There actually is no filter on a package list that allows you to filter by
                # id / href, so we'll have to just read them and can't guarantee that they're
                # actually in the repo / release.
                results = await PackageApi.read(thing)
                if results:
                    ret.append(results)
                else:
                    logger.warning(f"package_lookup was not found for {thing}!")
            else:
                query = params.copy()
                query.update(thing.dict(exclude_none=True))
                results = await PackageApi.list(params=query, type=package_type)
                if not results["results"]:
                    logger.warning(f"package_lookup was not found for {query}!")
                    continue
                if len(results["results"]) > 1:
                    logger.warning(f"Multiple packages found for {query}!")
                    continue
                ret.append(results["results"][0])
    else:
        ids = set(package_ids)
        found_ids = set()
        found_names = set()
        packages_by_name = defaultdict(list)
        name_field = package_type.pulp_name_field
        for pkg_query in package_queries:
            package = pkg_query.dict(exclude_none=True)
            packages_by_name[package[name_field]].append(package)

        # List the repo and match.
        async for package in yield_all(PackageApi.list, params=params, type=package_type):
            if request_size == 0:  # they want all
                ret.append(package)
            else:  # attempt to match the desired packages with the repo list
                if package["id"] in ids:
                    ret.append(package)
                    found_ids.add(package["id"])
                    continue
                if package[name_field] in packages_by_name:
                    for potential_match in packages_by_name[package[name_field]]:
                        if all(
                            potential_match[field] == package[field]
                            for field in package_type.natural_key_fields
                        ):
                            ret.append(package)
                            found_names.add(potential_match[package_type.pulp_name_field])
                            break

        missing_packages = []
        for name in packages_by_name.keys():
            if name not in found_names:
                missing_packages.append(name)
        for id in ids:
            if id not in found_ids:
                missing_packages.append(id)
        if missing_packages:
            logger.warning(
                f"package_lookup included {missing_packages}, but was not found for {params}!"
            )

    return ret
