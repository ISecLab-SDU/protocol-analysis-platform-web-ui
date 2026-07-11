"""Static-analysis database insight route registration."""

from __future__ import annotations

from typing import Callable

from flask import Blueprint


def register_static_analysis_insight_routes(
    bp: Blueprint,
    database_insights_handler: Callable[[], Callable[[], object]],
) -> dict[str, Callable[..., object]]:
    @bp.route("/static-analysis/database-insights", methods=["POST"])
    def static_analysis_database_insights():
        return database_insights_handler()()

    return {
        "static_analysis_database_insights": static_analysis_database_insights,
    }
