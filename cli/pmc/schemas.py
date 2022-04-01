from enum import Enum


class RepoType(str, Enum):
    """Type for a repository."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class DistroType(str, Enum):
    """Type for a distribution."""

    apt = "apt"
    yum = "yum"  # maps to 'rpm' in Pulp

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value


class Format(str, Enum):
    """Options for different response formats (e.g. json)."""

    json = "json"

    def __str__(self) -> str:
        """Return value as the string representation."""
        return self.value
