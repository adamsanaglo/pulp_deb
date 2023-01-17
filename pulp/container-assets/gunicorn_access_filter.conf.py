import logging

# https://stackoverflow.com/questions/52407736/how-to-filter-logs-from-gunicorn
class RequestPathFilter(logging.Filter):
    def __init__(self, *args, api_path, content_path, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_path = f"GET {content_path} HTTP"
        self.api_path = api_path

    def filter(self, record):
        # There's two different loggers that could be passing us records here, either the django
        # logger for pulp-api or the aiohttp logger for pulp-content. Unfortunately the aiohttp
        # logger only has the compiled msg available, and the django logger only has the
        # pre-compiled format string with a list of args available. So we have to handle them
        # differently. This could also conceivably be two completely different classes that are
        # loaded by the different gunicorn instances, but I think they're similar enough in intent
        # and function to keep together.
        if type(record.args) is type((1,)):  # record coming from the content logger
            return self.content_path not in record.msg
        req_path = record.args["U"]
        return self.api_path != req_path


def on_starting(server):
    # don't log health pings, which are for / on pulp-content or /pulp/api/v3/status/ on pulp-api
    server.log.access_log.addFilter(
        RequestPathFilter(api_path="/pulp/api/v3/status/", content_path="/")
    )
