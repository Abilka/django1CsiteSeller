from __future__ import annotations

from dataclasses import dataclass

from landing.models import MigrationPath, SiteSettings


@dataclass
class MigrationStepInfo:
    title: str
    description: str
    estimated_hours: float
    estimated_price: int


@dataclass
class MigrationEstimateResult:
    path_slug: str
    path_name: str
    source_name: str
    target_name: str
    description: str
    steps: list[MigrationStepInfo]
    total_hours: float
    total_price: int
    hourly_rate: int


def estimate_migration(
    migration_path: MigrationPath,
    site_settings: SiteSettings | None = None,
) -> MigrationEstimateResult:
    settings = site_settings or SiteSettings.load()
    hourly_rate = settings.hourly_rate
    steps: list[MigrationStepInfo] = []
    total_hours = 0.0

    for step in migration_path.steps.all():
        hours = float(step.estimated_hours)
        total_hours += hours
        steps.append(
            MigrationStepInfo(
                title=step.title,
                description=step.description,
                estimated_hours=hours,
                estimated_price=int(hours * hourly_rate),
            )
        )

    if not steps:
        hours = float(migration_path.base_hours)
        total_hours = hours
        steps.append(
            MigrationStepInfo(
                title='Миграция конфигурации',
                description=migration_path.description,
                estimated_hours=hours,
                estimated_price=int(hours * hourly_rate),
            )
        )

    return MigrationEstimateResult(
        path_slug=migration_path.slug,
        path_name=migration_path.name,
        source_name=migration_path.source_name,
        target_name=migration_path.target_name,
        description=migration_path.description,
        steps=steps,
        total_hours=total_hours,
        total_price=int(total_hours * hourly_rate),
        hourly_rate=hourly_rate,
    )
