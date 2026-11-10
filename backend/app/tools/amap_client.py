"""高德地图 Web 服务 API 客户端。

封装高德开放平台的 POI 搜索接口，供 POI 检索节点调用。

接口文档：https://lbs.amap.com/api/webservice/guide/api/search
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class AmapClient:
    """高德地图 Web 服务客户端（POI 搜索）。"""

    BASE_URL = "https://restapi.amap.com/v3/place/text"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.amap_api_key

    @property
    def is_configured(self) -> bool:
        """是否已配置 Key（未配置则无法调用真实接口）。"""
        return bool(self._api_key)

    async def search_poi(
        self,
        city: str,
        keywords: str,
        types: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """按关键字搜索 POI，返回标准化字典列表。

        :param city: 城市名（如"武汉"），也支持 adcode
        :param keywords: 检索关键字（如"江景 历史"或"景点"）
        :param types: 高德 POI 类型编码（可选，如"风景名胜"）
        :param limit: 返回条数上限
        :return: 标准化 POI 列表，每项含 name/category/location/cost/duration 等
        """
        if not self._api_key:
            return []

        params: dict[str, Any] = {
            "key": self._api_key,
            "city": city,
            "keywords": keywords,
            "offset": limit,
            "page": 1,
            "extensions": "base",
        }
        if types:
            params["types"] = types

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "1":
            # 高德返回非成功状态（如 key 无效、配额超限），返回空列表
            return []

        return self._normalize(data.get("pois", []))

    @staticmethod
    def _normalize(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把高德原始 POI 转为内部标准结构。"""
        result = []
        for i, p in enumerate(pois):
            # 高德 typecode 形如 "110101;110102"（数字编码），type 是中文文本（如"风景名胜"）。
            # 用 typecode 判断景点/美食，更可靠。
            raw_type = p.get("typecode", "") or p.get("type", "")
            category = "景点" if _looks_scenic(raw_type) else "美食"
            # 高德 location 为 "经度,纬度"，这里用区域+地址拼成可读位置
            location = _format_location(p.get("adname", ""), p.get("address", ""))

            result.append(
                {
                    "id": p.get("id", f"amap-{i}"),
                    "name": p.get("name", ""),
                    "category": category,
                    "location": location,
                    # 高德不直接给门票/人均费用，用 typecode 估算兜底
                    "estimated_cost": _estimate_cost(raw_type),
                    # 高德不直接给游玩时长，按类别估算
                    "estimated_duration": _estimate_duration(raw_type),
                    "address": p.get("address", ""),
                }
            )
        return result


def _looks_scenic(raw_type: str) -> bool:
    """根据高德 POI 类型编码判断是否为风景/景点类。

    兼容两种编码来源：
    - typecode：数字编码，如 "110200|170200|071100"（多级，用 | 分隔）
    - type：中文文本，如 "风景名胜;公园广场;公园"（用 ; 分隔）
    """
    scenic_codes = {
        "110100",  # 风景名胜
        "110200",  # 公园广场
        "110000",  # 风景名胜大类
        "140000",  # 科教文化服务
        "140300",  # 博物馆
        "140400",  # 展览馆
        "140500",  # 会展中心
        "140600",  # 美术馆
        "140700",  # 图书馆
        "140800",  # 科技馆
        "141000",  # 文化宫
    }
    scenic_words = ("风景", "公园", "博物馆", "展览馆", "美术馆", "图书馆", "科技馆", "文化宫", "会展")

    # 数字编码（typecode）和中文类型（type）可能混用 | 和 ; 分隔
    for code in raw_type.replace("|", ";").split(";"):
        code = code.strip()
        if not code:
            continue
        if code in scenic_codes or code.startswith("110") or code.startswith("140"):
            return True
        if any(w in code for w in scenic_words):
            return True
    return False


def _format_location(adname: str, address: str) -> str:
    """拼接区域 + 地址，作为粗略位置描述。"""
    parts = [p for p in [adname, address] if p]
    return " ".join(parts) if parts else ""


def _estimate_cost(raw_type: str) -> float:
    """按 POI 类型粗略估算人均费用（元）。"""
    if _looks_scenic(raw_type):
        return 60.0  # 景点门票平均估算
    return 50.0  # 美食人均估算


def _estimate_duration(raw_type: str) -> float:
    """按 POI 类型粗略估算游玩时长（小时）。"""
    if _looks_scenic(raw_type):
        return 2.0  # 景点通常 1.5-2.5 小时
    return 1.0  # 餐饮通常 1 小时
