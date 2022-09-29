from typing import Any, List, Optional

from fastapi import HTTPException

from app.core.schemas import ContentId, PackageId, RepoId, RepoType
from app.services.pulp.api import (
    PackageReleaseComponentApi,
    ReleaseApi,
    ReleaseComponentApi,
    RepositoryApi,
)


class ContentManager:
    """
    Adding or removing packages from a repo is simple for yum repos, but not apt.

    In apt repos there are also subdivisions called "releases", and further subdivisions called
    "components", and a package can be in one release and not another, or in one component and not
    another.

    pulp_deb manages this by allowing you to create Releases, and then allowing you to create
    ReleaseComponents for each component in that release, and finally allowing you to create
    PackageReleaseComponents, to map which packages are in each ReleaseComponent. A package is in
    a Release if it's in at least one ReleaseComponent in that release.

    PackageReleaseComponents, like "Packages", are a content type that you can pass to the repo
    "modify content" api. So when adding Packages we also want to add some PackageReleaseComponent
    objects to map them into the correct ReleaseComponents, and similarly when removing packages
    from a repo / release / component we need to also remove the PRC objects. And if we're removing
    the package from one release but it's still in another, then we actually want to ONLY remove
    the PRC object and not the package, since it's still being referenced.

    This class manages making those calculations, and does all communication with Pulp in
    minimalistic methods that the unit tests can mock out to isolate the logic.
    """

    def __init__(
        self, id: RepoId, release: Optional[str] = None, component: Optional[str] = None
    ) -> None:
        self.id = id
        self.release = release
        self.specified_release_id = None
        self.component = component

    async def add_and_remove_packages(
        self,
        add_packages: Optional[List[PackageId]] = None,
        remove_packages: Optional[List[PackageId]] = None,
    ) -> Any:
        """
        Translate package lists into content lists and then call out to
        server.app.services.pulp.api.RepositoryApi.update_content to update Pulp.
        """
        self.remove_content = [ContentId(pkg) for pkg in remove_packages or []]
        self.add_content = [ContentId(pkg) for pkg in add_packages or []]

        if self.id.type == RepoType.apt:
            if self.add_content and not self.release:
                raise HTTPException(
                    status_code=422,
                    detail="You must specify a release to add packages to an apt repo.",
                )

            # TODO: remove when bug is fixed. Un-skip the tests.
            if self.remove_content and self.release:
                raise HTTPException(
                    status_code=422,
                    detail="Due to a known bug you cannot currently remove a package from only one "
                    "release. To work-around, remove the package from all releases in this repo "
                    "by excluding the release option, then add it back in to the releases where it "
                    "should still exist. To see what releases in this repo a package is currently "
                    'in, you may do "pmc repo releases list <repo_name> --package <package_id>". '
                    "To track this issue you may follow "
                    "https://msazure.visualstudio.com/One/_workitems/edit/15641546",
                )

            new_remove_content = []
            packages_we_cannot_remove = set()
            if self.release:
                # look up and set the ContentId of the specified release
                release_ids = await self._get_release_ids()
                self.specified_release_id = release_ids[0]
            if not self.release or self.remove_content:
                # If removing, we will have to look through all release to see if the packages
                # are mentioned somewhere else.
                release_ids = await self._get_release_ids(all=True)

            for release_id in release_ids:
                component_ids = await self._get_component_ids_in_release(release_id)
                for component_id in component_ids:
                    # add prc ids
                    if release_id is self.specified_release_id:
                        for pkg_id in self.add_content[:]:
                            prc_id = await self._find_or_create_prc(pkg_id, component_id)
                            self.add_content.append(prc_id)

                    # remove prc ids
                    for pkg_id in self.remove_content:
                        prc_id = await self._find_prc(pkg_id, component_id)
                        if prc_id:
                            if not self.release:
                                # remove from all releases if not specified
                                new_remove_content.append(prc_id)
                            elif release_id == self.specified_release_id:
                                # or remove from the specified release, as requested
                                new_remove_content.append(prc_id)
                            else:
                                # still in a ReleaseComponent that we're not removing it from
                                packages_we_cannot_remove.add(pkg_id)

            # add the packages it's safe to remove back in to new_remove_content
            for pkg in self.remove_content:
                if pkg not in packages_we_cannot_remove:
                    new_remove_content.append(pkg)

            self.remove_content = new_remove_content

        return await self._update_pulp()

    async def _get_release_ids(self, all: bool = False) -> List[ContentId]:
        """
        Get list of relevant release ids, which may only be one if release was specified.
        If releases is specified set self.specified_release_id for later use.
        """
        params = {"repository": self.id}
        if not all:
            params["distribution"] = self.release
        async with ReleaseApi() as release_api:
            releases = await release_api.list(params=params)
        return [ContentId(x["id"]) for x in releases["results"]]

    async def _get_component_ids_in_release(self, release_id: ContentId) -> List[ContentId]:
        """Get list of component ids in this release."""
        async with ReleaseComponentApi() as component_api:
            components = await component_api.list(
                params={"release": release_id.uuid, "component": self.component}
            )
        return [ContentId(x["id"]) for x in components["results"]]

    @staticmethod
    async def _find_or_create_prc(package_id: ContentId, component_id: ContentId) -> ContentId:
        async with PackageReleaseComponentApi() as prc_api:
            return await prc_api.find_or_create(package_id, component_id)

    @staticmethod
    async def _find_prc(package_id: ContentId, component_id: ContentId) -> Optional[ContentId]:
        async with PackageReleaseComponentApi() as prc_api:
            return await prc_api.find(package_id, component_id)

    async def _update_pulp(self) -> Any:
        async with RepositoryApi() as repo_api:
            return await repo_api.update_content(self.id, self.add_content, self.remove_content)
