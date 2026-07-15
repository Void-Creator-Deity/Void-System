"""HTTP adapter for the Reward Marketplace, retaining legacy shop paths."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_current_user, get_reward_marketplace
from api.http.responses import APIResponse
from api.http.schemas.reward_marketplace import PurchaseRequest
from core.reward_marketplace_contracts import RewardMarketplaceError
from errors import VoidSystemException
from modules.reward_marketplace.marketplace import RewardMarketplace


router = APIRouter(tags=["兑换中心"])


def _translate_error(exc: RewardMarketplaceError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.get("/api/shop/items", summary="获取兑换商品", response_model=APIResponse)
async def get_shop_items(
    category: Optional[str] = Query(None),
    marketplace: RewardMarketplace = Depends(get_reward_marketplace),
) -> APIResponse:
    return APIResponse(
        success=True,
        message="商品列表获取成功",
        data={"items": marketplace.list_items(category)},
    )


@router.post(
    "/api/shop/purchase/{item_id}",
    summary="兑换商品",
    response_model=APIResponse,
)
async def purchase_item(
    item_id: str,
    purchase_data: PurchaseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    marketplace: RewardMarketplace = Depends(get_reward_marketplace),
) -> APIResponse:
    try:
        result = marketplace.purchase(
            user_id=current_user["user_id"],
            item_id=item_id,
            quantity=purchase_data.quantity,
        )
    except RewardMarketplaceError as exc:
        raise _translate_error(exc) from exc

    return APIResponse(success=True, message="兑换成功", data=result)
