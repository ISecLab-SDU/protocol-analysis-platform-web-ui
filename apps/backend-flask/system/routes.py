"""System management endpoints (menus, roles, departments)."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from faker import Faker
from flask import Blueprint, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.data import MOCK_MENU_LIST, get_menu_ids
    from ..utils.responses import paginate, sleep, success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.data import MOCK_MENU_LIST, get_menu_ids
    from utils.responses import paginate, sleep, success_response, unauthorized

bp = Blueprint("system", __name__, url_prefix="/api/system")

faker = Faker("zh_CN")


def _format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _generate_department_child(pid: str) -> Dict[str, Any]:
    return {
        "id": faker.uuid4(),
        "pid": pid,
        "name": faker.company(),
        "status": random.choice([0, 1]),
        "createTime": _format_datetime(
            faker.date_time_between(
                start_date=datetime(2023, 1, 1), end_date=datetime(2023, 12, 31)
            )
        ),
        "remark": faker.sentence(),
    }


def _generate_departments(count: int) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for _ in range(count):
        dept_id = faker.uuid4()
        item: Dict[str, Any] = {
            "id": dept_id,
            "pid": 0,
            "name": faker.company(),
            "status": random.choice([0, 1]),
            "createTime": _format_datetime(
                faker.date_time_between(
                    start_date=datetime(2021, 1, 1), end_date=datetime(2022, 12, 31)
                )
            ),
            "remark": faker.sentence(),
        }
        if random.choice([True, False]):
            item["children"] = [
                _generate_department_child(dept_id)
                for _ in range(random.randint(1, 5))
            ]
        data.append(item)
    return data


DEPARTMENT_DATA = _generate_departments(10)

MENU_LIST = deepcopy(MOCK_MENU_LIST)
PATH_MAP: Dict[str, str] = {"/": "0"}
NAME_MAP: Dict[str, str] = {}


def _collect_menu_maps(menus: List[Dict[str, Any]]):
    for menu in menus:
        PATH_MAP[str(menu.get("path"))] = str(menu.get("id"))
        NAME_MAP[str(menu.get("name"))] = str(menu.get("id"))
        children = menu.get("children") or []
        if children:
            _collect_menu_maps(children)


_collect_menu_maps(MENU_LIST)

ROLE_DATA: List[Dict[str, Any]] = []
MENU_IDS = get_menu_ids(MENU_LIST)
for _ in range(100):
    created_at = faker.date_time_between(
        start_date=datetime(2022, 1, 1), end_date=datetime(2025, 1, 1)
    )
    ROLE_DATA.append(
        {
            "id": faker.uuid4(),
            "name": faker.catch_phrase(),
            "status": random.choice([0, 1]),
            "createTime": _format_datetime(created_at),
            "permissions": random.sample(MENU_IDS, k=random.randint(1, len(MENU_IDS))),
            "remark": faker.sentence(),
        }
    )


def _ensure_authenticated():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return None, unauthorized()
    return user, None


@bp.get("/dept/list")
def dept_list():
    _, error = _ensure_authenticated()
    if error:
        return error
    return success_response(deepcopy(DEPARTMENT_DATA))


@bp.post("/dept")
def dept_create():
    _, error = _ensure_authenticated()
    if error:
        return error
    sleep(600)
    return success_response(None)


@bp.put("/dept/<dept_id>")
def dept_update(dept_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error
    sleep(600)
    return success_response(None)


@bp.delete("/dept/<dept_id>")
def dept_delete(dept_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error
    sleep(600)
    return success_response(None)


@bp.get("/menu/list")
def menu_list():
    _, error = _ensure_authenticated()
    if error:
        return error
    return success_response(deepcopy(MENU_LIST))


@bp.get("/menu/path-exists")
def menu_path_exists():
    _, error = _ensure_authenticated()
    if error:
        return error
    path = request.args.get("path")
    menu_id = request.args.get("id")
    exists = False
    if path:
        key = str(path)
        exists = key in PATH_MAP and (menu_id is None or PATH_MAP[key] != str(menu_id))
    return success_response(bool(exists))


@bp.get("/menu/name-exists")
def menu_name_exists():
    _, error = _ensure_authenticated()
    if error:
        return error
    name = request.args.get("name")
    menu_id = request.args.get("id")
    exists = False
    if name:
        key = str(name)
        exists = key in NAME_MAP and (menu_id is None or NAME_MAP[key] != str(menu_id))
    return success_response(bool(exists))


def _filter_roles(
    roles: List[Dict[str, Any]],
    *,
    name: Optional[str],
    role_id: Optional[str],
    remark: Optional[str],
    start_time: Optional[str],
    end_time: Optional[str],
    status: Optional[str],
) -> List[Dict[str, Any]]:
    filtered = roles
    if name:
        lowered = name.lower()
        filtered = [item for item in filtered if lowered in item["name"].lower()]
    if role_id:
        lowered = role_id.lower()
        filtered = [item for item in filtered if lowered in item["id"].lower()]
    if remark:
        lowered = remark.lower()
        filtered = [
            item
            for item in filtered
            if item.get("remark", "").lower().find(lowered) != -1
        ]
    if start_time:
        filtered = [
            item for item in filtered if item["createTime"] >= str(start_time)
        ]
    if end_time:
        filtered = [item for item in filtered if item["createTime"] <= str(end_time)]
    if status in {"0", "1"}:
        filtered = [
            item for item in filtered if item["status"] == int(status)  # type: ignore[arg-type]
        ]
    return filtered


@bp.get("/role/list")
def role_list():
    _, error = _ensure_authenticated()
    if error:
        return error

    query = request.args
    page = int(query.get("page", 1))
    page_size = int(query.get("pageSize", 20))
    name = query.get("name")
    role_id = query.get("id")
    remark = query.get("remark")
    start_time = query.get("startTime")
    end_time = query.get("endTime")
    status = query.get("status")

    working = deepcopy(ROLE_DATA)
    working = _filter_roles(
        working,
        name=name,
        role_id=role_id,
        remark=remark,
        start_time=start_time,
        end_time=end_time,
        status=status,
    )

    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    paged, total = paginate(working, page, page_size)
    return success_response({"items": paged, "total": total})
