"""Config flow for Korea EV Charger."""
import logging
import asyncio
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_API_KEY, CONF_ZCODE, CONF_KEYWORD, CONF_STAT_ID, CONF_STAT_NM

_LOGGER = logging.getLogger(__name__)

class KoreaEVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Korea EV Charger."""

    VERSION = 1

    def __init__(self):
        self.api_key = None
        self.stations = {}

    async def async_step_user(self, user_input=None):
        """1단계: API 키 및 검색 조건 입력"""
        errors = {}
        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
            zscode = user_input[CONF_ZCODE]
            keyword = user_input[CONF_KEYWORD]

            session = async_get_clientsession(self.hass)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            
            # https 적용
            url = f"https://apis.data.go.kr/B552584/EvCharger/getChargerInfo?serviceKey={self.api_key}&pageNo=1&numOfRows=9999&zscode={zscode}&dataType=JSON"

            try:
                # 10초 타임아웃 추가 (무한 뺑뺑이 방지)
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json(content_type=None)
                            items = data.get("items", {}).get("item", [])
                            
                            for item in items:
                                stat_nm = item.get("statNm", "")
                                if keyword in stat_nm:
                                    stat_id = item.get("statId")
                                    self.stations[stat_id] = f"{stat_nm} ({item.get('busiNm')})"

                            if not self.stations:
                                errors["base"] = "no_stations"
                            else:
                                return await self.async_step_select_station()
                        else:
                            _LOGGER.error("API 응답 에러 상태코드: %s", response.status)
                            errors["base"] = "cannot_connect"
            except (asyncio.TimeoutError, Exception) as e:
                _LOGGER.error("API 통신/타임아웃 에러: %s", e)
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_ZCODE, default="11410"): str,
            vol.Required(CONF_KEYWORD, default="파크뷰"): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_select_station(self, user_input=None):
        """2단계: 검색된 충전소 목록 중 하나를 선택"""
        if user_input is not None:
            stat_id = user_input[CONF_STAT_ID]
            stat_nm = self.stations[stat_id]

            await self.async_set_unique_id(stat_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=stat_nm,
                data={
                    CONF_API_KEY: self.api_key,
                    CONF_STAT_ID: stat_id,
                    CONF_STAT_NM: stat_nm,
                },
            )

        data_schema = vol.Schema({
            vol.Required(CONF_STAT_ID): vol.In(self.stations)
        })

        return self.async_show_form(
            step_id="select_station", data_schema=data_schema
        )