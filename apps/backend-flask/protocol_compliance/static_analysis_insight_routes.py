"""Static-analysis database insight request handlers."""

from __future__ import annotations

from typing import Callable

def create_static_analysis_insight_handlers(
    database_insights_handler: Callable[[], Callable[[], object]],
) -> dict[str, Callable[..., object]]:
    def static_analysis_database_insights():
        return database_insights_handler()()

    return {
        "static_analysis_database_insights": static_analysis_database_insights,
    }
