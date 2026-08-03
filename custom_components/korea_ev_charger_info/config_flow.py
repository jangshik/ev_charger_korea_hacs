"""Config flow for Korea EV Charger."""
import logging
import voluptuous as vol
import aiohttp

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
            # WAF 차단 우회를 위한 User-Agent 추가
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "Accept": "application/json"
            }
            url = "http://apis.data.go.kr/B552584/EvCharger/getChargerInfo"
            params = {
                "serviceKey": self.api_key,
                "pageNo": "1",
                "numOfRows": "9999",
                "zscode": zscode,
                "dataType": "JSON" #[cite: 1]
            }

            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        items = data.get("items", {}).get("item", [])
                        
                        # 검색어로 충전소 필터링[cite: 1]
                        for item in items:
                            stat_nm = item.get("statNm", "")
                            if keyword in stat_nm:
                                stat_id = item.get("statId") #[cite: 1]
                                self.stations[stat_id] = f"{stat_nm} ({item.get('busiNm')})" #[cite: 1]

                        if not self.stations:
                            errors["base"] = "no_stations"
                        else:
                            return await self.async_step_select_station()
                    else:
                        errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("API 통신 에러: %s", e)
                errors["base"] = "cannot_connect"

        # 입력 폼 스키마 (기본값 세팅)
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

            # 기기 고유 등록
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

        # 동적 드롭다운 생성
        data_schema = vol.Schema({
            vol.Required(CONF_STAT_ID): vol.In(self.stations)
        })

        return self.async_show_form(
            step_id="select_station", data_schema=data_schema
        )