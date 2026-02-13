from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Optional

import aiofiles
import httpx
from chinese_calendar import is_holiday as cc_is_holiday
from chinese_calendar import is_workday as cc_is_workday

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import CALENDAR_CN_HOLIDAY_DIR

timer_logger = get_sub_logger("timer")


@dataclass(frozen=True)
class CnDayInfo:
    """中国日历信息（仅保留工作日判断所需字段）"""

    is_holiday: bool  # True = 休息日（周末/法定节假日/调休放假）；False = 工作日（含补班）
    name: str


class CnWorkdayService:
    """中国法定工作日判断服务（数据目录文件缓存 + 可选远程拉取）。"""

    def __init__(self) -> None:
        self._year_cache: Dict[int, Dict[str, CnDayInfo]] = {}
        self._year_locks: Dict[int, asyncio.Lock] = {}

    async def is_workday(self, target_date: date) -> Optional[bool]:
        """判断指定日期是否为工作日（含调休补班）。

        Returns:
            Optional[bool]:
            - True: 工作日（含补班）
            - False: 休息日（周末/法定节假日/调休放假）
            - None: 无法判断（远程不可用且无缓存）
        """
        try:
            # 强依赖：默认使用离线库判断（更稳定、更快）
            return bool(cc_is_workday(target_date))
        except Exception:
            # 极少数情况下离线库可能不覆盖未来年份；此时降级到远程 API + 文件缓存
            timer_logger.exception("离线工作日判断失败，将降级为远程 API")

        data = await self._get_year_data(target_date.year)
        if data is None:
            return None
        key = target_date.strftime("%Y-%m-%d")
        info = data.get(key)
        if info is None:
            return None
        return not info.is_holiday

    async def is_restday(self, target_date: date) -> Optional[bool]:
        """判断指定日期是否为休息日（周末/法定节假日/调休放假）。

        Returns:
            Optional[bool]:
            - True: 休息日
            - False: 工作日（含补班）
            - None: 无法判断
        """
        try:
            return bool(cc_is_holiday(target_date))
        except Exception:
            timer_logger.exception("离线休息日判断失败，将降级为远程 API")

        data = await self._get_year_data(target_date.year)
        if data is None:
            return None
        key = target_date.strftime("%Y-%m-%d")
        info = data.get(key)
        if info is None:
            return None
        return info.is_holiday

    def _get_cache_dir(self) -> Path:
        # 使用系统目录，避免污染用户文件；目录位于 OsEnv.DATA_DIR 下
        cache_dir = Path(CALENDAR_CN_HOLIDAY_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _year_cache_path(self, year: int) -> Path:
        return self._get_cache_dir() / f"allyear_{year}.json"

    async def _get_year_data(self, year: int) -> Optional[Dict[str, CnDayInfo]]:
        if year in self._year_cache:
            return self._year_cache[year]

        lock = self._year_locks.setdefault(year, asyncio.Lock())
        async with lock:
            if year in self._year_cache:
                return self._year_cache[year]

            cache_path = self._year_cache_path(year)
            payload = await self._read_cache_file(cache_path)
            if payload is not None:
                try:
                    parsed = self._parse_allyear_payload(payload)
                except Exception:
                    timer_logger.exception(f"解析中国节假日缓存文件失败: year={year}")
                else:
                    self._year_cache[year] = parsed
                    return parsed

            payload = await self._fetch_allyear(year)
            if payload is None:
                return None

            parsed = self._parse_allyear_payload(payload)
            self._year_cache[year] = parsed

            await self._write_cache_file(cache_path, payload)
            return parsed

    async def _read_cache_file(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                raw = await f.read()
            data = json.loads(raw)
        except Exception:
            timer_logger.exception(f"读取中国节假日缓存文件失败: path={path}")
            return None
        if not isinstance(data, dict) or data.get("code") != 0:
            return None
        return data

    async def _write_cache_file(self, path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(payload, ensure_ascii=False))
            tmp_path.replace(path)
        except Exception:
            timer_logger.exception(f"写入中国节假日缓存文件失败: path={path}")

    async def _fetch_allyear(self, year: int) -> Optional[dict]:
        """调用 holiday.ailcc.com 的 allyear 接口获取全年每天信息。"""
        url = f"https://holiday.ailcc.com/api/holiday/allyear/{year}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            timer_logger.exception(f"拉取中国节假日数据失败: year={year}")
            return None

        if not isinstance(data, dict) or data.get("code") != 0:
            timer_logger.error(f"拉取中国节假日数据失败: year={year}, resp={data!r}")
            return None
        return data

    def _parse_allyear_payload(self, payload: dict) -> Dict[str, CnDayInfo]:
        raw_list = payload.get("data")
        if not isinstance(raw_list, list):
            raise TypeError("allyear payload missing 'data' list")  # noqa: TRY003

        result: Dict[str, CnDayInfo] = {}
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            d = item.get("date")
            is_holiday = item.get("is_holiday")
            name = item.get("name") or ""
            if not isinstance(d, str):
                continue
            if is_holiday not in (0, 1):
                continue
            result[d] = CnDayInfo(is_holiday=bool(is_holiday), name=str(name))
        return result


cn_workday_service = CnWorkdayService()

