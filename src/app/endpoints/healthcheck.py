from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/kaithhealthcheck")
async def kaith_healthcheck():
    return {"status": "ok"}
