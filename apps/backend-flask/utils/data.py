"""Static mock data shared across Flask endpoints."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

MOCK_USERS: List[Dict[str, Any]] = [
    {
        "id": 0,
        "password": "123456",
        "realName": "Vben",
        "roles": ["super"],
        "username": "vben",
    },
    {
        "id": 1,
        "password": "123456",
        "realName": "Admin",
        "roles": ["admin"],
        "username": "admin",
        "homePath": "/workspace",
    },
    {
        "id": 2,
        "password": "123456",
        "realName": "Jack",
        "roles": ["user"],
        "username": "jack",
        "homePath": "/analytics",
    },
]

MOCK_CODES = [
    {
        "username": "vben",
        "codes": ["AC_100100", "AC_100110", "AC_100120", "AC_100010"],
    },
    {
        "username": "admin",
        "codes": ["AC_100010", "AC_100020", "AC_100030"],
    },
    {
        "username": "jack",
        "codes": ["AC_1000001", "AC_1000002"],
    },
]

DASHBOARD_MENUS = [
    {
        "meta": {
            "order": -1,
            "title": "page.dashboard.title",
        },
        "name": "Dashboard",
        "path": "/dashboard",
        "redirect": "/analytics",
        "children": [
            {
                "name": "Analytics",
                "path": "/analytics",
                "component": "/dashboard/analytics/index",
                "meta": {
                    "affixTab": True,
                    "title": "page.dashboard.analytics",
                },
            },
            {
                "name": "Workspace",
                "path": "/workspace",
                "component": "/dashboard/workspace/index",
                "meta": {
                    "title": "page.dashboard.workspace",
                },
            },
        ],
    },
]


def create_demos_menus(role: str) -> List[Dict[str, Any]]:
    role_with_menus = {
        "admin": {
            "component": "/demos/access/admin-visible",
            "meta": {
                "icon": "mdi:button-cursor",
                "title": "demos.access.adminVisible",
            },
            "name": "AccessAdminVisibleDemo",
            "path": "/demos/access/admin-visible",
        },
        "super": {
            "component": "/demos/access/super-visible",
            "meta": {
                "icon": "mdi:button-cursor",
                "title": "demos.access.superVisible",
            },
            "name": "AccessSuperVisibleDemo",
            "path": "/demos/access/super-visible",
        },
        "user": {
            "component": "/demos/access/user-visible",
            "meta": {
                "icon": "mdi:button-cursor",
                "title": "demos.access.userVisible",
            },
            "name": "AccessUserVisibleDemo",
            "path": "/demos/access/user-visible",
        },
    }

    return [
        {
            "meta": {
                "icon": "ic:baseline-view-in-ar",
                "keepAlive": True,
                "order": 1000,
                "title": "demos.title",
            },
            "name": "Demos",
            "path": "/demos",
            "redirect": "/demos/access",
            "children": [
                {
                    "name": "AccessDemos",
                    "path": "/demosaccess",
                    "meta": {
                        "icon": "mdi:cloud-key-outline",
                        "title": "demos.access.backendPermissions",
                    },
                    "redirect": "/demos/access/page-control",
                    "children": [
                        {
                            "name": "AccessPageControlDemo",
                            "path": "/demos/access/page-control",
                            "component": "/demos/access/index",
                            "meta": {
                                "icon": "mdi:page-previous-outline",
                                "title": "demos.access.pageAccess",
                            },
                        },
                        {
                            "name": "AccessButtonControlDemo",
                            "path": "/demos/access/button-control",
                            "component": "/demos/access/button-control",
                            "meta": {
                                "icon": "mdi:button-cursor",
                                "title": "demos.access.buttonControl",
                            },
                        },
                        {
                            "name": "AccessMenuVisible403Demo",
                            "path": "/demos/access/menu-visible-403",
                            "component": "/demos/access/menu-visible-403",
                            "meta": {
                                "authority": ["no-body"],
                                "icon": "mdi:button-cursor",
                                "menuVisibleWithForbidden": True,
                                "title": "demos.access.menuVisible403",
                            },
                        },
                        deepcopy(role_with_menus[role]),
                    ],
                },
            ],
        },
    ]


def _clone_menu(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return deepcopy(items)


MOCK_MENUS = [
    {
        "username": "vben",
        "menus": _clone_menu(DASHBOARD_MENUS) + create_demos_menus("super"),
    },
    {
        "username": "admin",
        "menus": _clone_menu(DASHBOARD_MENUS) + create_demos_menus("admin"),
    },
    {
        "username": "jack",
        "menus": _clone_menu(DASHBOARD_MENUS) + create_demos_menus("user"),
    },
]

MOCK_MENU_LIST: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Workspace",
        "status": 1,
        "type": "menu",
        "icon": "mdi:dashboard",
        "path": "/workspace",
        "component": "/dashboard/workspace/index",
        "meta": {
            "icon": "carbon:workspace",
            "title": "page.dashboard.workspace",
            "affixTab": True,
            "order": 0,
        },
    },
    {
        "id": 2,
        "meta": {
            "icon": "carbon:settings",
            "order": 9997,
            "title": "system.title",
            "badge": "new",
            "badgeType": "normal",
            "badgeVariants": "primary",
        },
        "status": 1,
        "type": "catalog",
        "name": "System",
        "path": "/system",
        "children": [
            {
                "id": 201,
                "pid": 2,
                "path": "/system/menu",
                "name": "SystemMenu",
                "authCode": "System:Menu:List",
                "status": 1,
                "type": "menu",
                "meta": {
                    "icon": "carbon:menu",
                    "title": "system.menu.title",
                },
                "component": "/system/menu/list",
                "children": [
                    {
                        "id": 20_101,
                        "pid": 201,
                        "name": "SystemMenuCreate",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Menu:Create",
                        "meta": {"title": "common.create"},
                    },
                    {
                        "id": 20_102,
                        "pid": 201,
                        "name": "SystemMenuEdit",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Menu:Edit",
                        "meta": {"title": "common.edit"},
                    },
                    {
                        "id": 20_103,
                        "pid": 201,
                        "name": "SystemMenuDelete",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Menu:Delete",
                        "meta": {"title": "common.delete"},
                    },
                ],
            },
            {
                "id": 202,
                "pid": 2,
                "path": "/system/dept",
                "name": "SystemDept",
                "status": 1,
                "type": "menu",
                "authCode": "System:Dept:List",
                "meta": {
                    "icon": "carbon:container-services",
                    "title": "system.dept.title",
                },
                "component": "/system/dept/list",
                "children": [
                    {
                        "id": 20_401,
                        "pid": 201,
                        "name": "SystemDeptCreate",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Dept:Create",
                        "meta": {"title": "common.create"},
                    },
                    {
                        "id": 20_402,
                        "pid": 201,
                        "name": "SystemDeptEdit",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Dept:Edit",
                        "meta": {"title": "common.edit"},
                    },
                    {
                        "id": 20_403,
                        "pid": 201,
                        "name": "SystemDeptDelete",
                        "status": 1,
                        "type": "button",
                        "authCode": "System:Dept:Delete",
                        "meta": {"title": "common.delete"},
                    },
                ],
            },
        ],
    },
    {
        "id": 9,
        "meta": {
            "badgeType": "dot",
            "order": 9998,
            "title": "demos.vben.title",
            "icon": "carbon:data-center",
        },
        "name": "Project",
        "path": "/vben-admin",
        "type": "catalog",
        "status": 1,
        "children": [
            {
                "id": 901,
                "pid": 9,
                "name": "VbenDocument",
                "path": "/vben-admin/document",
                "component": "IFrameView",
                "type": "embedded",
                "status": 1,
                "meta": {
                    "icon": "carbon:book",
                    "iframeSrc": "https://doc.vben.pro",
                    "title": "demos.vben.document",
                },
            },
            {
                "id": 902,
                "pid": 9,
                "name": "VbenGithub",
                "path": "/vben-admin/github",
                "component": "IFrameView",
                "type": "link",
                "status": 1,
                "meta": {
                    "icon": "carbon:logo-github",
                    "link": "https://github.com/vbenjs/vue-vben-admin",
                    "title": "Github",
                },
            },
            {
                "id": 903,
                "pid": 9,
                "name": "VbenAntdv",
                "path": "/vben-admin/antdv",
                "component": "IFrameView",
                "type": "link",
                "status": 0,
                "meta": {
                    "icon": "carbon:hexagon-vertical-solid",
                    "badgeType": "dot",
                    "link": "https://ant.vben.pro",
                    "title": "demos.vben.antdv",
                },
            },
        ],
    },
    {
        "id": 10,
        "component": "_core/about/index",
        "type": "menu",
        "status": 1,
        "meta": {
            "icon": "lucide:copyright",
            "order": 9999,
            "title": "demos.vben.about",
        },
        "name": "About",
        "path": "/about",
    },
]


def get_menu_ids(menus: List[Dict[str, Any]]) -> List[int]:
    ids: List[int] = []
    for item in menus:
        ids.append(int(item["id"]))
        children = item.get("children") or []
        if children:
            ids.extend(get_menu_ids(children))
    return ids
