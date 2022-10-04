from gettext import gettext as _  # noqa

from django_filters import Filter
from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.viewsets import (
    ContentFilter,
    ContentViewSet,
    NamedModelViewSet,
    SingleArtifactContentUploadViewSet,
)

from pulp_deb.app import models, serializers


class GenericContentFilter(ContentFilter):
    """
    FilterSet for GenericContent.
    """

    class Meta:
        model = models.GenericContent
        fields = ["relative_path", "sha256"]


class GenericContentViewSet(SingleArtifactContentUploadViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    GenericContent is a catch all category for storing files not covered by any other type.

    Associated artifacts: Exactly one arbitrary file that does not match any other type.

    This is needed to store arbitrary files for use with the verbatim publisher. If you are not
    using the verbatim publisher, you may ignore this type.
    """

    endpoint_name = "generic_contents"
    queryset = models.GenericContent.objects.prefetch_related("_artifacts")
    serializer_class = serializers.GenericContentSerializer
    filterset_class = GenericContentFilter


class ContentRelationshipFilter(Filter):
    """
    Base class for filters that allow you to ask meaningful questions about the relationships of
    deb-specific content types. Subclasses must provide a HELP message and implement _filter.

    The value for all these filters is a string that is a comma-separated 2-tuple, where the second
    value is the HREF of the RepositoryVersion you care about. This is logically necessary if you
    want to ask any question beyond "list Package|ReleaseComponent|whatever that were ever at any
    point in this Repository|Release|whatever". I will try to explain by example.

    Question: "What Packages are in the most recent RepositoryVersion of a Release?"

    Imagine we have a very simple repo with two packages and two releases, and this state is stored
    in RepositoryVersion1:
    Repository -> Release1 -> ReleaseComponent1 -> PackageReleaseComponent1 -> Package1
                                                -> PackageReleaseComponent2 -> Package2
               -> Release2 -> ReleaseComponent2 -> PackageReleaseComponent3 -> Package2

    We then update the repo to remove Package2 from ReleaseComponent1 and this state gets stored
    in RepositoryVersion2:
    Repository -> Release1 -> ReleaseComponent1 -> PackageReleaseComponent1 -> Package1
               -> Release2 -> ReleaseComponent2 -> PackageReleaseComponent3 -> Package2

    We could try answer the question using the existing ContentFilter.repository_version filter in
    conjunction with a new filter that naively follows the foreign key references in the database:
    packages.filter(deb_packagereleasecomponent__release_component__release=release_uuid)

    What Django does if you call two separate filters is use the first to filter the QuerySet,
    then use the second to filter the QuerySet further. This is *different* than calling
    filter once with both conditions.
    https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships

    Example: packages.filter("in RepositoryVersion2").filter("in Release1")
    This will return both Package1 and Package2, which is not what we wanted. In the first filter it
    looks and says "yep, both Package1 and Package2 are in RepositoryVersion2", and then the second
    filter is applied and it says "yep, both Package1 and Package2 were in Release1 at some point".
    This is because the linkage via PackageReleaseComponent2 still *exists*, it's just not in
    RepositoryVersion2.

    What we really _actually_ want is to apply _both_ conditions to the PackageReleaseComponent
    mapping as an intermediate step, so both release_uuid and repository_version_href must be
    passed to our new filter:
    packages.filter(package.PRC in PRC.filter("in RepositoryVersion2", "in Release1"))

    This guarantees that we are only considering Packages with both requirements, and returns only
    Package1.
    """

    HELP = "Override with your value-specific help message"
    GENERIC_HELP = """
    Must be a comma-separated string: "value,repository_version_href"
    value: %s
    repository_version_href: The RepositoryVersion href to filter by
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("help_text", _(self.GENERIC_HELP) % _(self.HELP))
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Content Queryset
            value (string, "value,repository_version_href"): The values to filter by
        """
        if value is None:
            # user didn't supply a value
            return qs

        my_value, repo_version_href = value.split(",", 1)
        if not my_value or not repo_version_href or "," in repo_version_href:
            # malformed input, bail
            return qs

        repo_version = NamedModelViewSet.get_resource(repo_version_href, RepositoryVersion)
        prc_qs = models.PackageReleaseComponent.objects.filter(pk__in=repo_version.content)

        return self._filter(qs, my_value, prc_qs)

    def _filter(self, qs, value, prc_qs):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Content Queryset
            value (string): The values to filter by
            prc_qs (django.db.models.query.QuerySet): QuerySet of PackageReleaseComponents in
                requested RepositoryVersion
        """
        raise NotImplementedError


class PackageToReleaseComponentFilter(ContentRelationshipFilter):
    HELP = "(ReleaseComponent uuid) Filter results where Package in ReleaseComponent"

    def _filter(self, qs, value, prc_qs):
        prc_qs = prc_qs.filter(release_component=value)
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class PackageToReleaseFilter(ContentRelationshipFilter):
    HELP = "(Release uuid) Filter results where Package in Release"

    def _filter(self, qs, value, prc_qs):
        prc_qs = prc_qs.filter(release_component__release=value)
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class PackageFilter(ContentFilter):
    """
    FilterSet for Package.
    """

    release_component = PackageToReleaseComponentFilter()
    release = PackageToReleaseFilter()

    class Meta:
        model = models.Package
        fields = [
            "package",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "sha256",
            "relative_path",
        ]


class PackageViewSet(SingleArtifactContentUploadViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A Package represents a '.deb' binary package.

    Associated artifacts: Exactly one '.deb' package file.
    """

    endpoint_name = "packages"
    queryset = models.Package.objects.prefetch_related("_artifacts")
    serializer_class = serializers.PackageSerializer
    filterset_class = PackageFilter


class InstallerPackageFilter(ContentFilter):
    """
    FilterSet for InstallerPackage.
    """

    class Meta:
        model = models.InstallerPackage
        fields = [
            "package",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "sha256",
        ]


class InstallerPackageViewSet(SingleArtifactContentUploadViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An InstallerPackage represents a '.udeb' installer package.

    Associated artifacts: Exactly one '.udeb' installer package file.

    Note that installer packages are currently used exclusively for verbatim publications. The APT
    publisher (both simple and structured mode) will not include these packages.
    """

    endpoint_name = "installer_packages"
    queryset = models.InstallerPackage.objects.prefetch_related("_artifacts")
    serializer_class = serializers.InstallerPackageSerializer
    filterset_class = InstallerPackageFilter


# Metadata


class ReleaseFileFilter(ContentFilter):
    """
    FilterSet for ReleaseFile.
    """

    class Meta:
        model = models.ReleaseFile
        fields = ["codename", "suite", "relative_path", "sha256"]


class ReleaseFileViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseFile represents the Release file(s) from a single APT distribution.

    Associated artifacts: At least one of 'Release' and 'InRelease' file. If the 'Release' file is
    present, then there may also be a 'Release.gpg' detached signature file for it.

    Note: The verbatim publisher will republish all associated artifacts, while the APT publisher
    (both simple and structured mode) will generate any 'Release' files it needs when creating the
    publication. It does not make use of ReleaseFile content.
    """

    endpoint_name = "release_files"
    queryset = models.ReleaseFile.objects.all()
    serializer_class = serializers.ReleaseFileSerializer
    filterset_class = ReleaseFileFilter


class PackageIndexFilter(ContentFilter):
    """
    FilterSet for PackageIndex.
    """

    class Meta:
        model = models.PackageIndex
        fields = ["component", "architecture", "relative_path", "sha256"]


class PackageIndexViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A PackageIndex represents the package indices of a single component-architecture combination.

    Associated artifacts: Exactly one 'Packages' file. May optionally include one or more of
    'Packages.gz', 'Packages.xz', 'Release'. If included, the 'Release' file is a legacy
    per-component-and-architecture Release file.

    Note: The verbatim publisher will republish all associated artifacts, while the APT publisher
    (both simple and structured mode) will generate any 'Packages' files it needs when creating the
    publication. It does not make use of PackageIndex content.
    """

    endpoint_name = "package_indices"
    queryset = models.PackageIndex.objects.all()
    serializer_class = serializers.PackageIndexSerializer
    filterset_class = PackageIndexFilter


class InstallerFileIndexFilter(ContentFilter):
    """
    FilterSet for InstallerFileIndex.
    """

    class Meta:
        model = models.InstallerFileIndex
        fields = ["component", "architecture", "relative_path", "sha256"]


class InstallerFileIndexViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An InstallerFileIndex represents the indices for a set of installer files.

    Associated artifacts: Exactly one 'SHA256SUMS' and/or 'MD5SUMS' file.

    Each InstallerFileIndes is associated with a single component-architecture combination within
    a single Release. Note that installer files are currently used exclusively for verbatim
    publications. The APT publisher (both simple and structured mode) does not make use of installer
    content.
    """

    endpoint_name = "installer_file_indices"
    queryset = models.InstallerFileIndex.objects.all()
    serializer_class = serializers.InstallerFileIndexSerializer
    filterset_class = InstallerFileIndexFilter


class ReleaseToPackageFilter(ContentRelationshipFilter):
    HELP = "(Package uuid) Filter results where Release contains Package"

    def _filter(self, qs, value, prc_qs):
        prc_qs = prc_qs.filter(package=value)
        return qs.filter(deb_releasecomponent__deb_packagereleasecomponent__in=prc_qs)


class ReleaseFilter(ContentFilter):
    """
    FilterSet for Release.
    """

    package = ReleaseToPackageFilter()

    class Meta:
        model = models.Release
        fields = ["codename", "suite", "distribution"]


class ReleaseViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A Release represents a single APT release/distribution.

    Associated artifacts: None; contains only metadata.

    Note that in the context of the "Release content", the terms "distribution" and "release"
    are synonyms. An "APT repository release/distribution" is associated with a single 'Release'
    file below the 'dists/' folder. The "distribution" refers to the path between 'dists/' and the
    'Release' file. The "distribution" could be considered the name of the "release". It is often
    (but not always) equal to the "codename" or "suite".
    """

    endpoint_name = "releases"
    queryset = models.Release.objects.all()
    serializer_class = serializers.ReleaseSerializer
    filterset_class = ReleaseFilter


class ReleaseArchitectureFilter(ContentFilter):
    """
    FilterSet for ReleaseArchitecture.
    """

    class Meta:
        model = models.ReleaseArchitecture
        fields = ["architecture", "release"]


class ReleaseArchitectureViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseArchitecture represents a single dpkg architecture string.

    Associated artifacts: None; contains only metadata.

    Every ReleaseArchitecture is always associated with exactly one Release. This indicates that
    the release/distribution in question supports this architecture.
    """

    endpoint_name = "release_architectures"
    queryset = models.ReleaseArchitecture.objects.all()
    serializer_class = serializers.ReleaseArchitectureSerializer
    filterset_class = ReleaseArchitectureFilter


class ReleaseComponentToPackageFilter(ContentRelationshipFilter):
    HELP = "(Package uuid) Filter results where ReleaseComponent contains Package"

    def _filter(self, qs, value, prc_qs):
        prc_qs = prc_qs.filter(package=value)
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class ReleaseComponentFilter(ContentFilter):
    """
    FilterSet for ReleaseComponent.
    """

    package = ReleaseComponentToPackageFilter()

    class Meta:
        model = models.ReleaseComponent
        fields = ["component", "release"]


class ReleaseComponentViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseComponent represents a single APT repository component.

    Associated artifacts: None; contains only metadata.

    Every ReleaseComponent is always associated with exactly one Release. This indicates that the
    release/distribution in question contains this component.
    """

    endpoint_name = "release_components"
    queryset = models.ReleaseComponent.objects.all()
    serializer_class = serializers.ReleaseComponentSerializer
    filterset_class = ReleaseComponentFilter


class PackageReleaseComponentFilter(ContentFilter):
    """
    FilterSet for PackageReleaseComponent.
    """

    class Meta:
        model = models.PackageReleaseComponent
        fields = ["package", "release_component"]


class PackageReleaseComponentViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A PackageReleaseComponent associates a Package with a ReleaseComponent.

    Associated artifacts: None; contains only metadata.

    This simply stores the information which packages are part of which components.
    """

    endpoint_name = "package_release_components"
    queryset = models.PackageReleaseComponent.objects.all()
    serializer_class = serializers.PackageReleaseComponentSerializer
    filterset_class = PackageReleaseComponentFilter