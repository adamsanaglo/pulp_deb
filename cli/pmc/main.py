import typer

from .commands import package, repository

app = typer.Typer()
app.add_typer(repository.app, name="repo")
app.add_typer(package.app, name="package")

if __name__ == "__main__":
    app()
