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

    def __init__(self, hass, api_key, stat_id, interval, timeout):
        """Initialize."""
        self.api_key = api_key
        self.stat_id = stat_id
        self.timeout_sec = timeout # 💡 타임아웃 저장
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
            # 💡 UI에서 설정한 동적 타임아웃 적용 (기본 20초)
            async with asyncio.timeout(self.timeout_sec):
                async with self.session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.warning("API 통신 지연 또는 상태 에러(%s). 이전 센서 데이터를 유지합니다.", response.status)
                        return self.data # 💡 에러 시 기존 데이터 반환
                    
                    data = await response.json(content_type=None)
                    items = data.get("items", {}).get("item", [])
                    
                    if not items:
                        _LOGGER.warning("해당 충전소 데이터를 찾을 수 없습니다. 이전 데이터를 유지합니다.")
                        return self.data # 💡 데이터 누락 시에도 기존 데이터 반환
                        
                    chargers = {}
                    for item in items:
                        chger_id = item.get("chgerId")
                        if chger_id:
                            chargers[chger_id] = item
                            
                    return chargers

        except Exception as err:
            _LOGGER.warning("API 통신 중 예외 발생(%s). 이전 센서 데이터를 유지합니다.", err)
            # 💡 통신 타임아웃, JSON 파싱 에러 등 모든 예외 상황에서도 기존 데이터 반환
            return self.data