import json

import httpx
import typer

try:
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter
    from pygments.lexers import JsonLexer
except ImportError:
    PYGMENTS = False
else:
    PYGMENTS = True
    PYGMENTS_STYLE = "dracula"


def output_response(resp: httpx.Response) -> None:
    output = json.dumps(resp.json(), indent=3)
    if PYGMENTS:
        formatter = Terminal256Formatter(style=PYGMENTS_STYLE)
        output = highlight(output, JsonLexer(), formatter)
    typer.secho(output)
