import pkg_resources


class NamedString(str):
    name = ""

    @property
    def title(self) -> str:
        return self.name.title()


LIST_SEPARATOR = NamedString(",")
LIST_SEPARATOR.name = "comma"

CLI_VERSION = pkg_resources.get_distribution("pmc-cli").version
