"""DataUpdateCoordinator for Korea EV Charger."""
import logging
import async_timeout

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
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        url = "http://apis.data.go.kr/B552584/EvCharger/getChargerInfo"
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "99",
            "statId": self.stat_id, #[cite: 1]
            "dataType": "JSON" #[cite: 1]
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        try:
            async with async_timeout.timeout(30):
                response = await self.session.get(url, params=params, headers=headers)
                if response.status != 200:
                    raise UpdateFailed(f"Error communicating with API: {response.status}")
                
                data = await response.json(content_type=None)
                items = data.get("items", {}).get("item", [])
                
                # statId 기준 모든 충전기 데이터를 dict 형태로 정리
                chargers = {}
                for item in items:
                    chger_id = item.get("chgerId") #[cite: 1]
                    chargers[chger_id] = item

                return chargers
                
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}")