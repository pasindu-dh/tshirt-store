from fastapi import APIRouter

from app.config import settings
from app.schemas.return_request import (
    ReturnPolicyOut,
    ReturnReasonOut,
)
from app.services.returns import RETURN_REASONS

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("/policy", response_model=ReturnPolicyOut)
def get_return_policy():
    return ReturnPolicyOut(
        window_days=settings.return_window_days,
        policy_text=settings.return_policy_text,
        reasons=[
            ReturnReasonOut(code=code, label=label)
            for code, label in RETURN_REASONS
        ],
    )
