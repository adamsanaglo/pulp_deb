import pytest
from fastapi.exceptions import HTTPException
from tests.utils import (
    gen_package_id,
    gen_package_release_component_id,
    gen_release_component_id,
    gen_release_id,
    gen_repo_id,
)

from app.core.schemas import RepoType

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_yum_is_easy(content_manager):
    cm = content_manager(gen_repo_id(RepoType.yum))
    add_pkg = gen_package_id()
    remove_pkg = gen_package_id()

    await cm.add_and_remove_packages([add_pkg], [remove_pkg])

    cm._get_release_ids.assert_not_called()
    cm._get_component_ids_in_release.assert_not_called()
    cm._find_or_create_prc.assert_not_called()
    cm._find_prc.assert_not_called()
    cm._update_pulp.assert_called_once()
    # adding/removing just the packages
    assert set(cm.add_content) == set([add_pkg])
    assert set(cm.remove_content) == set([remove_pkg])


async def test_apt_adding_requires_release(content_manager):
    cm = content_manager(gen_repo_id(RepoType.apt))
    try:
        await cm.add_and_remove_packages([gen_package_id()], None)
    except HTTPException as e:
        assert "You must specify a release to add packages to an apt repo." in e.detail
    else:
        assert False, "Expected exception not thrown!"


async def test_apt_adding_adds_prc(content_manager):
    cm = content_manager(gen_repo_id(RepoType.apt), release="test", component="main")
    release = gen_release_id()
    component = gen_release_component_id()
    prc = gen_package_release_component_id()
    cm._get_release_ids.return_value = [release]
    cm._get_component_ids_in_release.return_value = [component]
    cm._find_or_create_prc.return_value = prc
    add_pkg = gen_package_id()

    await cm.add_and_remove_packages([add_pkg], None)

    cm._find_prc.assert_not_called()
    cm._update_pulp.assert_called_once()
    # adding both package and prc
    assert set(cm.add_content) == set([add_pkg, prc])
    assert set(cm.remove_content) == set()


async def test_apt_removing_removes_prc(content_manager):
    cm = content_manager(gen_repo_id(RepoType.apt), release="test", component="main")
    release = gen_release_id()
    component = gen_release_component_id()
    prc = gen_package_release_component_id()
    cm._get_release_ids.return_value = [release]
    cm._get_component_ids_in_release.return_value = [component]
    cm._find_prc.return_value = prc
    remove_pkg = gen_package_id()

    await cm.add_and_remove_packages(None, [remove_pkg])

    cm._find_or_create_prc.assert_not_called()
    cm._update_pulp.assert_called_once()
    assert set(cm.add_content) == set()
    # removing both package and prc
    assert set(cm.remove_content) == set([remove_pkg, prc])


async def test_apt_multiple_releases_doesnt_remove_package(content_manager):
    cm = content_manager(gen_repo_id(RepoType.apt), release="test", component="main")
    release1 = gen_release_id()
    release2 = gen_release_id()
    component1 = gen_release_component_id()
    component2 = gen_release_component_id()
    prc1 = gen_package_release_component_id()
    prc2 = gen_package_release_component_id()
    # Should get called exactly twice, once to look up the release id of the "test" release we
    # specified, and once to get all of them in the repo. Returns the 1st list first, then the 2nd.
    cm._get_release_ids.side_effect = ([release1], [release1, release2])
    cm._get_component_ids_in_release.side_effect = ([component1], [component2])
    cm._find_prc.side_effect = (prc1, prc2)
    remove_pkg = gen_package_id()

    await cm.add_and_remove_packages(None, [remove_pkg])

    cm._find_or_create_prc.assert_not_called()
    cm._update_pulp.assert_called_once()
    assert set(cm.add_content) == set()
    # removing *only* the prc in the release requested (release1)
    assert set(cm.remove_content) == set([prc1])


async def test_apt_remove_from_all_releases(content_manager):
    # not specifying release here to remove from all releases
    cm = content_manager(gen_repo_id(RepoType.apt))
    release1 = gen_release_id()
    release2 = gen_release_id()
    component1 = gen_release_component_id()
    component2 = gen_release_component_id()
    prc1 = gen_package_release_component_id()
    prc2 = gen_package_release_component_id()
    # Only called once to get all releases
    cm._get_release_ids.return_value = [release1, release2]
    cm._get_component_ids_in_release.side_effect = ([component1], [component2])
    cm._find_prc.side_effect = (prc1, prc2)
    remove_pkg = gen_package_id()

    await cm.add_and_remove_packages(None, [remove_pkg])

    cm._find_or_create_prc.assert_not_called()
    cm._update_pulp.assert_called_once()
    assert set(cm.add_content) == set()
    # removing the package and both prcs
    assert set(cm.remove_content) == set([remove_pkg, prc1, prc2])


async def test_apt_missing_release_throws_sensible_error(content_manager):
    cm = content_manager(gen_repo_id(RepoType.apt), release="test", component="main")
    cm._get_release_ids.return_value = []

    try:
        await cm.add_and_remove_packages([gen_package_id()], None)
    except HTTPException as e:
        assert e.status_code == 422
        assert "Specified release not found!" in e.detail
    else:
        assert False, "Expected exception not thrown!"
