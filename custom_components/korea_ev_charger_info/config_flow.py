"""Config flow for Korea EV Charger."""
import logging
import asyncio
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_API_KEY, CONF_ZCODE, CONF_KEYWORD, CONF_STAT_ID, CONF_STAT_NM, REGION_CODES

_LOGGER = logging.getLogger(__name__)

class KoreaEVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.api_key = None
        self.stations = {}

    async def async_step_user(self, user_input=None):
        """1단계: API 키 입력 (최초 1회만 노출)"""
        
        # 💡 이전에 등록된 기기에서 API 키를 찾아보고, 존재하면 바로 2단계(검색)로 점프!
        existing_entries = self._async_current_entries()
        if existing_entries:
            saved_key = existing_entries[0].data.get(CONF_API_KEY)
            if saved_key:
                self.api_key = saved_key
                return await self.async_step_search()

        errors = {}
        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
            return await self.async_step_search()

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_search(self, user_input=None):
        """2단계: 지역 및 검색어 입력"""
        errors = {}
        if user_input is not None:
            zscode = user_input[CONF_ZCODE]
            keyword = user_input[CONF_KEYWORD]

            session = async_get_clientsession(self.hass)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json"
            }
            
            url = f"https://apis.data.go.kr/B552584/EvCharger/getChargerInfo?serviceKey={self.api_key}&pageNo=1&numOfRows=9999&zscode={zscode}&dataType=JSON"

            try:
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
                            errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("API Error: %s", e)
                errors["base"] = "cannot_connect"

        region_options = [
            selector.SelectOptionDict(value=code, label=name)
            for code, name in REGION_CODES.items()
        ]

        # 💡 기본값(default)을 모두 제거하여 빈칸으로 시작하게 합니다.
        data_schema = vol.Schema({
            vol.Required(CONF_ZCODE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=region_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Required(CONF_KEYWORD): str,
        })

        return self.async_show_form(
            step_id="search", data_schema=data_schema, errors=errors
        )

    async def async_step_select_station(self, user_input=None):
        """3단계: 검색된 충전소 목록 중 하나를 선택"""
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