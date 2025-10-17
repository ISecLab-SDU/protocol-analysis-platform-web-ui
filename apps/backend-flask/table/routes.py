"""Table demo endpoints."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from functools import cmp_to_key
from typing import Any, Dict, List, Tuple

from faker import Faker
from flask import Blueprint, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import paginate, sleep, success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import paginate, sleep, success_response, unauthorized

bp = Blueprint("table", __name__, url_prefix="/api/table")

faker = Faker()


def _generate_table_item() -> Dict[str, Any]:
    release_date = faker.date_time_this_decade()
    line_start = faker.pyint(min_value=10, max_value=300)
    return {
        "id": faker.uuid4(),
        "imageUrl": faker.image_url(),
        "imageUrl2": faker.image_url(),
        "open": faker.pybool(),
        "status": faker.random_element(["success", "error", "warning"]),
        "productName": faker.catch_phrase(),
        "price": f"{faker.pydecimal(left_digits=4, right_digits=2, positive=True)}",
        "currency": faker.currency_code(),
        "quantity": faker.pyint(min_value=1, max_value=100),
        "available": faker.pybool(),
        "category": faker.bs(),
        "releaseDate": release_date.isoformat(),
        "rating": round(faker.pyfloat(min_value=1, max_value=5), 2),
        "description": faker.text(),
        "weight": round(faker.pyfloat(min_value=0.1, max_value=10), 2),
        "color": faker.color_name(),
        "inProduction": faker.pybool(),
        "tags": [faker.word() for _ in range(3)],
        "lineRange": [line_start, line_start + faker.pyint(min_value=2, max_value=14)],
    }


TABLE_DATA: List[Dict[str, Any]] = [_generate_table_item() for _ in range(100)]


def _as_number(value: Any) -> Tuple[bool, float]:
    try:
        return True, float(value)
    except (TypeError, ValueError):
        return False, 0.0


def _as_datetime(value: Any) -> Tuple[bool, datetime]:
    if isinstance(value, str):
        try:
            return True, datetime.fromisoformat(value)
        except ValueError:
            return False, datetime.min
    return False, datetime.min


def _compare_values(a_value: Any, b_value: Any) -> int:
    if isinstance(a_value, bool) and isinstance(b_value, bool):
        if a_value == b_value:
            return 0
        return 1 if a_value else -1

    if isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
        return (a_value > b_value) - (a_value < b_value)

    a_is_dt, a_dt = _as_datetime(a_value)
    b_is_dt, b_dt = _as_datetime(b_value)
    if a_is_dt and b_is_dt:
        return (a_dt > b_dt) - (a_dt < b_dt)

    a_is_num, a_num = _as_number(a_value)
    b_is_num, b_num = _as_number(b_value)
    if a_is_num and b_is_num:
        return (a_num > b_num) - (a_num < b_num)

    a_str = str(a_value)
    b_str = str(b_value)
    if a_str == b_str:
        return 0
    return -1 if a_str < b_str else 1


@bp.get("/list")
def table_list():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()

    sleep(600)

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    sort_by = request.args.get("sortBy")
    sort_order = request.args.get("sortOrder")

    working = deepcopy(TABLE_DATA)
    if working and sort_by and sort_by in working[0]:
        reverse = sort_order == "desc"

        def comparator(a: Dict[str, Any], b: Dict[str, Any]) -> int:
            result = _compare_values(a.get(sort_by), b.get(sort_by))
            return -result if reverse else result

        working.sort(key=cmp_to_key(comparator))

    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    paged, total = paginate(working, page, page_size)
    return success_response({"items": paged, "total": total})
