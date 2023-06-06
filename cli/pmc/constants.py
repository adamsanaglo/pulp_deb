from importlib.metadata import version


class NamedString(str):
    name = ""

    def __new__(cls, value: str, name: str) -> "NamedString":
        obj = super().__new__(cls, value)
        obj.name = name
        return obj

    @property
    def Name(self) -> str:
        return self.name.title()


LIST_SEPARATOR = NamedString(",", name="comma")

CLI_VERSION = version("pmc-cli")
