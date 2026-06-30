from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from landing.models import PriceListItem, SiteSettings, TypicalTask


@dataclass
class TaskEstimateItem:
    kind: str
    item_id: int
    title: str
    category: str
    hours: float
    price: int


@dataclass
class TaskEstimateResult:
    items: list[TaskEstimateItem]
    total_hours: float
    total_price: int
    hourly_rate: int


def _hours_midpoint(hours_from: Decimal | None, hours_to: Decimal | None) -> float:
    if hours_from is not None and hours_to is not None:
        return float((hours_from + hours_to) / 2)
    if hours_from is not None:
        return float(hours_from)
    if hours_to is not None:
        return float(hours_to)
    return 0.0


def estimate_tasks(
    typical_task_ids: list[int],
    price_item_ids: list[int],
    site_settings: SiteSettings | None = None,
) -> TaskEstimateResult:
    settings = site_settings or SiteSettings.load()
    hourly_rate = settings.hourly_rate
    items: list[TaskEstimateItem] = []

    for task in TypicalTask.objects.filter(pk__in=typical_task_ids, is_published=True):
        hours = float(task.estimated_hours)
        items.append(
            TaskEstimateItem(
                kind='typical_task',
                item_id=task.pk,
                title=task.title,
                category='Типовые задачи',
                hours=hours,
                price=int(hours * hourly_rate),
            )
        )

    for price_item in PriceListItem.objects.filter(pk__in=price_item_ids, is_published=True):
        hours = _hours_midpoint(price_item.hours_from, price_item.hours_to)
        items.append(
            TaskEstimateItem(
                kind='price_item',
                item_id=price_item.pk,
                title=price_item.name,
                category=price_item.get_category_display(),
                hours=hours,
                price=int(hours * hourly_rate),
            )
        )

    total_hours = sum(item.hours for item in items)
    total_price = sum(item.price for item in items)
    return TaskEstimateResult(
        items=items,
        total_hours=total_hours,
        total_price=total_price,
        hourly_rate=hourly_rate,
    )
