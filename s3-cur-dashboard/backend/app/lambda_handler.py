"""Entry point AWS Lambda invokes.

Mangum adapts Lambda's event format (both classic API Gateway proxy events
and the newer Function URL / HTTP API v2 payload) into ASGI calls against
the same FastAPI app used for local/uvicorn development -- no route or
business logic changes needed to run on Lambda.
"""

from mangum import Mangum

from .main import app

handler = Mangum(app, lifespan="off")
