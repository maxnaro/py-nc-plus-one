from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from nc_plus_one.auth.router import router as auth_router
from nc_plus_one.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from nc_plus_one.events.router import router as events_router
from nc_plus_one.rsvps.router import router as rsvps_router

TITLE = "NC Plus One"
API = "api"
ERROR = "error"
APPLICATION_ERROR_STATUS = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
}

app = FastAPI(title=TITLE, debug=True)
app.include_router(events_router, prefix=f"/{API}", tags=[API])
app.include_router(rsvps_router, prefix=f"/{API}", tags=[API])
app.include_router(auth_router, prefix=f"/{API}", tags=[API])


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={ERROR: exc.detail})


@app.exception_handler(ApplicationError)
def handle_application_error(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=APPLICATION_ERROR_STATUS[type(exc)],
        content={ERROR: {"code": exc.code, "message": str(exc)}},
    )
