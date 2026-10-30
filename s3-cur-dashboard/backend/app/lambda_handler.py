"""Entry point AWS Lambda invokes.

Two shapes of event reach this function:
- A normal HTTP request (API Gateway proxy event) -- handled by Mangum,
  which adapts it into an ASGI call against the same FastAPI app used for
  local/uvicorn development, so there's no route/logic fork.
- An internal async "job" invocation this same function sent itself (see
  main.py's _dispatch_job) to run a slow CUR load in the background,
  outside any HTTP request's timeout. These carry a "cur_job" key instead
  of the usual API Gateway event shape and are handled directly, without
  going through Mangum/FastAPI routing at all.
"""

from mangum import Mangum

from .main import _execute_job, app
from .schemas import CurLoadRequest

_mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    cur_job = event.get("cur_job") if isinstance(event, dict) else None
    if cur_job is not None:
        _execute_job(cur_job["job_id"], CurLoadRequest(**cur_job["request"]))
        return {"ok": True}
    return _mangum_handler(event, context)
