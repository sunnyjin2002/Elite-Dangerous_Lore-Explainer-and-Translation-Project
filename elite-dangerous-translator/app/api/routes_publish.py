"""Publishing route placeholders."""

from fastapi import APIRouter

router = APIRouter(prefix="/publish", tags=["publish"])


@router.get("/status")
def publish_status() -> dict[str, str]:
    """Return placeholder publishing status."""
    return {"status": "not configured"}
