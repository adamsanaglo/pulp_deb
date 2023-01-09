import pytest

from app.core.schemas import (
    PackageType,
    Pagination,
    RepoType,
    StrictDebPackageQuery,
    StrictFilePackageQuery,
    StrictPythonPackageQuery,
    StrictRpmPackageQuery,
)
from app.services.pulp import package_lookup as package_lookup_module
from app.services.pulp import utils as utils_module

from .utils import gen_list_attrs, gen_package_attrs, gen_repo_id

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_yield_all(repository_api):
    """Test that the yield_all utility function is depaginating results correctly."""
    pagination = Pagination(limit=3)
    repository_api.list.side_effect = (
        gen_list_attrs([1, 2, 3], count=7),
        gen_list_attrs([4, 5, 6], count=7),
        gen_list_attrs([7], count=7),
    )

    results = set()
    async for result in utils_module.yield_all(repository_api.list, pagination, "arg", kwarg=1):
        results.add(result)

    assert results == set(range(1, 8))
    assert repository_api.list.call_count == 3
    repository_api.list.assert_called_with(
        pagination, "arg", kwarg=1, params={"ordering": "pulp_created"}
    )


def _gen_packages(package_type, total, desired):
    """Generates packages and returns them and expected packages, ids / names / queries"""
    packages = [gen_package_attrs(package_type) for _ in range(total)]
    desired_packages, ids, names, filenames, queries = [], set(), set(), set(), []
    t_2_q = {
        PackageType.deb: StrictDebPackageQuery,
        PackageType.file: StrictFilePackageQuery,
        PackageType.python: StrictPythonPackageQuery,
        PackageType.rpm: StrictRpmPackageQuery,
    }
    for i in range(desired):
        package = packages[i]
        desired_packages.append(package)
        ids.add(package["id"])
        names.add(package[package_type.pulp_name_field])
        filenames.add(package[package_type.pulp_filename_field])
        query = t_2_q[package_type](**package)
        queries.append(query)
    return packages, desired_packages, ids, names, filenames, queries


def _assert_expected_packages(
    package_type, found, expected_ids, expected_names, expected_filenames
):
    found_ids = {x["id"] for x in found}
    found_names = {x[package_type.pulp_name_field] for x in found}
    found_filenames = {x[package_type.pulp_filename_field] for x in found}
    assert found_ids == expected_ids
    assert found_names == expected_names
    assert found_filenames == expected_filenames


@pytest.mark.parametrize("repo_type", (RepoType.apt, RepoType.yum, RepoType.file, RepoType.python))
async def test_package_lookup_all(package_api, repository_api, repo_type):
    """Test that package_lookup returns all packages in the repo when asked."""
    repo_id = gen_repo_id(repo_type)
    package_type = repo_type.package_type
    packages, _, expd_ids, expd_names, expd_filenames, _ = _gen_packages(package_type, 15, 15)
    package_api.list.return_value = gen_list_attrs(packages)

    found = await package_lookup_module.package_lookup(repo=repo_id)

    _assert_expected_packages(package_type, found, expd_ids, expd_names, expd_filenames)


@pytest.mark.parametrize("lookup_type", ("apt", "yum", "file", "python", "by_id"))
async def test_package_lookup_small(package_api, repository_api, lookup_type):
    """Test that package_lookup returns the correct packages for small lookups."""
    by_id = lookup_type == "by_id"
    repo_type = RepoType("apt" if by_id else lookup_type)
    repo_id = gen_repo_id(repo_type)
    package_type = repo_type.package_type
    _, expd_pkgs, expd_ids, expd_names, expd_filenames, queries = _gen_packages(package_type, 15, 3)
    package_api.list.side_effect = [gen_list_attrs([p]) for p in expd_pkgs]
    package_api.read.side_effect = [p for p in expd_pkgs]

    if by_id:
        found = await package_lookup_module.package_lookup(repo=repo_id, package_ids=list(expd_ids))
    else:
        found = await package_lookup_module.package_lookup(repo=repo_id, package_queries=queries)

    if by_id:
        assert package_api.list.call_count == 0
        assert package_api.read.call_count == 3
    else:
        assert package_api.list.call_count == 3
        assert package_api.read.call_count == 0
    _assert_expected_packages(package_type, found, expd_ids, expd_names, expd_filenames)


@pytest.mark.parametrize("lookup_type", ("apt", "yum", "file", "python", "by_id"))
async def test_package_lookup_large(package_api, repository_api, lookup_type):
    """Test that package_lookup returns the correct packages for large lookups."""
    by_id = lookup_type == "by_id"
    repo_type = RepoType("apt" if by_id else lookup_type)
    repo_id = gen_repo_id(repo_type)
    package_type = repo_type.package_type
    packages, _, expd_ids, expd_names, expd_filenames, queries = _gen_packages(package_type, 15, 12)
    package_api.list.return_value = gen_list_attrs(packages)

    if by_id:
        found = await package_lookup_module.package_lookup(repo=repo_id, package_ids=list(expd_ids))
    else:
        found = await package_lookup_module.package_lookup(repo=repo_id, package_queries=queries)

    _assert_expected_packages(package_type, found, expd_ids, expd_names, expd_filenames)
