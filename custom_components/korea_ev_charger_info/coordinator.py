"""DataUpdateCoordinator for Korea EV Charger."""
import logging
import async_timeout
from datetime import timedelta # 상단 추가

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class KoreaEVCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass, api_key, stat_id):
        """Initialize."""
        self.api_key = api_key
        self.stat_id = stat_id
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval), # 동적 주기 반영
        )

    async def _async_update_data(self):
        """Update data via API."""
        url = f"https://apis.data.go.kr/B552584/EvCharger/getChargerInfo?serviceKey={self.api_key}&pageNo=1&numOfRows=99&statId={self.stat_id}&dataType=JSON"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url, headers=headers)
                if response.status != 200:
                    raise UpdateFailed(f"Error communicating with API: {response.status}")
                
                data = await response.json(content_type=None)
                items = data.get("items", {}).get("item", [])
                
                chargers = {}
                for item in items:
                    chger_id = item.get("chgerId")
                    chargers[chger_id] = item

                return chargers
                
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}")