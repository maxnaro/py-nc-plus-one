from typing import Annotated

from fastapi import APIRouter, Depends, status

from nc_plus_one.auth.dependencies import require_token
from nc_plus_one.rsvps import service

# RSVPs are a separate feature exposed beneath the existing event URLs.
router = APIRouter(prefix="/events", tags=["events"])


@router.post("/{id}/rsvp", status_code=status.HTTP_201_CREATED)
def rsvp(id: int, payload: Annotated[dict, Depends(require_token)]):
    return service.create_rsvp(id, payload["sub"])


@router.delete("/{id}/rsvp/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_rsvp(id: int, payload: Annotated[dict, Depends(require_token)]):
    service.delete_rsvp(id, payload["sub"])
