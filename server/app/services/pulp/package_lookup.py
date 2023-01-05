import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from app.core.schemas import (
    PackageId,
    RepoId,
    StrictDebPackageQuery,
    StrictFilePackageQuery,
    StrictPythonPackageQuery,
    StrictRpmPackageQuery,
)
from app.services.pulp.api import PackageApi, RepositoryApi
from app.services.pulp.utils import yield_all

logger = logging.getLogger(__name__)


async def package_lookup(
    repo: RepoId,
    release: Optional[str] = None,
    package_ids: Optional[List[PackageId]] = None,
    package_queries: Optional[
        List[
            Union[
                StrictDebPackageQuery,
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
    type = repo.package_type
    # Let's only bother loading the id and identifying fields of the package here.
    params["fields"] = ",".join(type.natural_key_fields + ["pulp_href"])
    # Look up the current repo version once so we don't have to do it for each package list page.
    params["repository_version"] = await RepositoryApi.latest_version_href(repo)
    if release:
        params["release"] = release

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
                results = await PackageApi.list(params=query, type=type)
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
        name_field = type.pulp_name_field
        for query in package_queries:
            package = query.dict(exclude_none=True)
            packages_by_name[package[name_field]].append(package)

        # List the repo and match.
        async for package in yield_all(PackageApi.list, params=params, type=type):
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
                            for field in type.natural_key_fields
                        ):
                            ret.append(package)
                            found_names.add(potential_match[type.pulp_name_field])
                            break

        for name in packages_by_name.keys():
            if name not in found_names:
                logger.warning(f"package_lookup included {name}, but was not found for {params}!")
        for id in ids:
            if id not in found_ids:
                logger.warning(f"package_lookup included {id}, but was not found for {params}!")

    return ret
