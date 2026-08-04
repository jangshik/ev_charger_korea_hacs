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
        errors = {}
        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
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

        # === 💡 변경 포인트: 기존 API 키 불러오기 ===
        existing_entries = self._async_current_entries()
        saved_api_key = ""
        if existing_entries:
            # 이전에 등록된 첫 번째 기기에서 API 키를 가져옵니다.
            saved_api_key = existing_entries[0].data.get(CONF_API_KEY, "")

        # 스키마 구성: API 키가 있으면 default 값으로 박아줍니다.
        api_key_schema = vol.Required(CONF_API_KEY, default=saved_api_key) if saved_api_key else vol.Required(CONF_API_KEY)

        region_options = [
            selector.SelectOptionDict(value=code, label=name)
            for code, name in REGION_CODES.items()
        ]

        data_schema = vol.Schema({
            api_key_schema: str,
            vol.Required(CONF_ZCODE, default="11410"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=region_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
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