from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.schemas import ContentId, PackageId, PackageType, ReleaseId, RepoId, RepoType
from app.services.pulp.api import (
    PackageReleaseComponentApi,
    ReleaseApi,
    ReleaseArchitectureApi,
    ReleaseComponentApi,
    RepositoryApi,
)
from app.services.pulp.package_lookup import package_lookup
from app.services.pulp.utils import id_to_pulp_href


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
        self,
        id: RepoId,
        release: Optional[str] = None,
        component: Optional[str] = None,
        architecture: Optional[str] = None,
    ) -> None:
        self.id = id
        self.release = release
        self.specified_release_id = None
        self.component = component
        self.architecture = architecture

    async def add_and_remove_packages(
        self,
        add_packages: Optional[List[PackageId]] = None,
        remove_packages: Optional[List[PackageId]] = None,
    ) -> Any:
        """
        Translate package lists into content lists and then call out to
        server.app.services.pulp.api.RepositoryApi.update_content to update Pulp.
        """
        await self._translate_packages(add_packages, remove_packages)
        return await self._update_pulp()

    async def remove_release(self, release_id: ReleaseId) -> Any:
        """Remove a Release and all its various related Content/Packages."""
        packages = await package_lookup(
            repo=self.id, package_type=PackageType.deb, release=release_id
        )
        packages += await package_lookup(
            repo=self.id, package_type=PackageType.deb_src, release=release_id
        )
        package_ids = [pkg["id"] for pkg in packages]
        await self._translate_packages(remove_packages=package_ids)

        self.remove_content.append(ContentId(release_id))
        self.remove_content.extend(await self._get_component_ids_in_release(release_id))
        self.remove_content.extend(await self._get_arch_ids_in_release(release_id))

        return await self._update_pulp()

    async def _translate_packages(
        self,
        add_packages: Optional[List[PackageId]] = None,
        remove_packages: Optional[List[PackageId]] = None,
    ) -> None:
        """
        Translate lists of packages to content.

        Also adds necessary related content like PackageReleaseComponents to lists.
        """
        self.remove_content = [ContentId(pkg) for pkg in remove_packages or []]
        self.add_content = [ContentId(pkg) for pkg in add_packages or []]

        if self.id.type == RepoType.apt:
            if self.add_content and not self.release:
                raise HTTPException(
                    status_code=422,
                    detail="You must specify a release to add packages to an apt repo.",
                )

            new_remove_content = []
            packages_we_cannot_remove = set()
            release_ids = []
            if self.release:
                # look up and set the ContentId of the specified release
                release_ids = await self._get_release_ids()
                if not release_ids:
                    raise HTTPException(status_code=422, detail="Specified release not found!")
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

    async def _get_release_ids(self, all: bool = False) -> List[ContentId]:
        """
        Get list of relevant release ids, which may only be one if release was specified.
        """
        params: Dict[str, Any] = {"repository": self.id}
        if not all:
            params["distribution"] = self.release
        releases = await ReleaseApi.list(params=params)
        return [ContentId(x["id"]) for x in releases["results"]]

    async def _get_component_ids_in_release(self, release_id: ContentId) -> List[ContentId]:
        """Get list of component ids in this release."""
        components = await ReleaseComponentApi.list(
            params={"release": id_to_pulp_href(release_id), "component": self.component}
        )
        return [ContentId(x["id"]) for x in components["results"]]

    async def _get_arch_ids_in_release(self, release_id: ContentId) -> List[ContentId]:
        """Get list of component ids in this release."""
        architectures = await ReleaseArchitectureApi.list(
            params={"release": id_to_pulp_href(release_id), "architecture": self.architecture}
        )
        return [ContentId(x["id"]) for x in architectures["results"]]

    @staticmethod
    async def _find_or_create_prc(package_id: ContentId, component_id: ContentId) -> ContentId:
        return await PackageReleaseComponentApi.find_or_create(PackageId(package_id), component_id)

    @staticmethod
    async def _find_prc(package_id: ContentId, component_id: ContentId) -> Optional[ContentId]:
        return await PackageReleaseComponentApi.find(PackageId(package_id), component_id)

    async def _update_pulp(self) -> Any:
        return await RepositoryApi.update_content(self.id, self.add_content, self.remove_content)
