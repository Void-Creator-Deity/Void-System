"""Stable reward catalog exposed through the legacy shop API."""
from __future__ import annotations

from typing import Any, Dict, Tuple


MARKETPLACE_ITEMS: Tuple[Dict[str, Any], ...] = (
    {
        "item_id": "item_energy_small",
        "item_name": "小型能量药水",
        "price": 50,
        "category": "consumable",
        "description": "恢复 10 点成长属性",
        "icon": "💊",
        "effect": {"attr_restore": 10},
    },
    {
        "item_id": "item_energy_medium",
        "item_name": "中型能量药水",
        "price": 150,
        "category": "consumable",
        "description": "恢复 30 点成长属性",
        "icon": "⚗️",
        "effect": {"attr_restore": 30},
    },
    {
        "item_id": "item_energy_large",
        "item_name": "大型能量药水",
        "price": 300,
        "category": "consumable",
        "description": "恢复 50 点成长属性",
        "icon": "🔭",
        "effect": {"attr_restore": 50},
    },
    {
        "item_id": "item_task_accelerator",
        "item_name": "任务加速器",
        "price": 200,
        "category": "tool",
        "description": "减少任务完成时间 20%",
        "icon": "⚡",
        "effect": {"task_time_reduction": 0.2},
    },
    {
        "item_id": "item_coin_detector",
        "item_name": "金币探测器",
        "price": 350,
        "category": "tool",
        "description": "增加任务奖励金币 15%",
        "icon": "📵",
        "effect": {"coin_bonus": 0.15},
    },
    {
        "item_id": "item_experience_boost",
        "item_name": "经验加速器",
        "price": 250,
        "category": "tool",
        "description": "增加获得经验值 20%",
        "icon": "💌",
        "effect": {"exp_bonus": 0.2},
    },
)

ITEMS_BY_ID = {item["item_id"]: item for item in MARKETPLACE_ITEMS}
