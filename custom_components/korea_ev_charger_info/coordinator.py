"""DataUpdateCoordinator for Korea EV Charger."""
import logging
from datetime import timedelta
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# 💡 더 이상 존재하지 않는 UPDATE_INTERVAL을 import 하지 않습니다.
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class KoreaEVCoordinator(DataUpdateCoordinator):
    """Class to manage fetching EV charger data."""

    def __init__(self, hass, api_key, stat_id, interval):
        """Initialize."""
        self.api_key = api_key
        self.stat_id = stat_id
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval), # 동적으로 받은 주기를 사용
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        url = f"https://apis.data.go.kr/B552584/EvCharger/getChargerInfo?serviceKey={self.api_key}&pageNo=1&numOfRows=99&statId={self.stat_id}&dataType=JSON"
        
        try:
            # HA 최신 버전 권장 방식인 asyncio.timeout 적용
            async with asyncio.timeout(10):
                async with self.session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"API 통신 에러 발생: {response.status}")
                    
                    data = await response.json(content_type=None)
                    items = data.get("items", {}).get("item", [])
                    
                    if not items:
                        _LOGGER.warning("해당 충전소(%s)의 데이터를 찾을 수 없습니다.", self.stat_id)
                        return {}
                        
                    chargers = {}
                    for item in items:
                        chger_id = item.get("chgerId")
                        if chger_id:
                            chargers[chger_id] = item
                            
                    return chargers

        except Exception as err:
            raise UpdateFailed(f"API 통신 중 예외 발생: {err}")