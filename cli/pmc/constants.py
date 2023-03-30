class NamedString(str):
    name = ""

    @property
    def title(self) -> str:
        return self.name.title()


LIST_SEPARATOR = NamedString(",")
LIST_SEPARATOR.name = "comma"
