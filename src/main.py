from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from src.routes.events import router as events_router

TITLE = "NC Plus One"
API = "api"
ERROR = "error"

app = FastAPI(title=TITLE, debug=True)
app.include_router(events_router, prefix=f"/{API}", tags=[API])


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={ERROR: exc.detail})
