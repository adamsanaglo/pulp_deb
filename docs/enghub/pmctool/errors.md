# Errors

When using the CLI, there are two general types of failures that you may encounter: API/CLI errors and
task failures.


## API/CLI Errors

When you encounter an error, the return code of the pmc CLI command will be non-zero,
and stdout will be a json structure such as the one below.
The message field will give some general information about the error.
The detail field will either be a string or a mapping of particular field names to error messages.
If the problem occurred while the CLI command communicated with the back-end service, the `url` and `correlation_id` fields will be populated
while the `http_status` field will be a value other than -1.

```json
{
   "message": "400 Client Error: Bad Request for url: http://localhost:8000/api/v4/repositories/",
   "http_status": 400,
   "url": "http://localhost:8000/api/v4/repositories/",
   "detail": {
      "name": [
         "This field must be unique."
      ]
   },
   "correlation_id": "1661106e9838476dad76a0d82667507e"
}
```

## Task Failures

When you perform an asynchronous operation, it's possible that the operation will fail.
In this case, you'll see a failed task such as the one below.
You can check either that the state is "failed" and/or that error is not null.

```json
{
   "id": "tasks-544827d8-e631-4d69-8e88-c3f41fe15eb9",
   "pulp_created": "2023-06-02T17:26:10.831898+00:00",
   "state": "failed",
   "name": "pulpcore.app.tasks.repository.add_and_remove",
   "logging_cid": "b6e96b38-f07c-4e8e-bc1f-2ca483a95cef",
   "started_at": "2023-06-02T17:26:10.861346+00:00",
   "finished_at": "2023-06-02T17:26:11.001787+00:00",
   "error": {
      "traceback": "  File \"/usr/lib/python3.9/site-packages/pulpcore/tasking/pulpcore_worker.py\", line 458, in _perform_task\n    result = func(*args, **kwargs)\n  File \"/usr/lib/python3.9/site-packages/pulpcore/app/tasks/repository.py\", line 230, in add_and_remove\n    new_version.add_content(models.Content.objects.filter(pk__in=add_content_units))\n  File \"/usr/lib/python3.9/site-packages/pulpcore/app/models/repository.py\", line 1094, in __exit__\n    raise ValueError(\n",
      "description": "Saw unsupported content types {'deb.package'}"
   },
   "worker": "workers-51322e91-1fba-4b6a-8469-3d7b63643726",
   "progress_reports": [],
   "created_resources": [],
   "reserved_resources_record": [
      "/pulp/api/v3/repositories/rpm/rpm/2a887fee-ace5-45c8-9938-6b6eeb6fc2cc/"
   ]
}
```
