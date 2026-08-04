"""Sensor platform for Korea EV Charger."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_STAT_ID, CONF_STAT_NM, STAT_MAPPING, TYPE_MAPPING

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    stat_id = entry.data[CONF_STAT_ID]
    stat_nm = entry.data[CONF_STAT_NM]

    entities = []
    # 1. 충전소 통합 상태 센서 (사용 가능한 완속/급속 개수 요약)
    entities.append(StationSummarySensor(coordinator, stat_id, stat_nm))

    # 2. 각 개별 충전기 포트별 센서 생성
    for chger_id in coordinator.data:
        entities.append(ChargerPortSensor(coordinator, stat_id, stat_nm, chger_id))

    async_add_entities(entities)


class StationSummarySensor(CoordinatorEntity, SensorEntity):
    """충전소 전체 사용 가능한 충전기 수 (메인 센서)"""

    def __init__(self, coordinator, stat_id, stat_nm):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.stat_nm = stat_nm
        self._attr_name = f"{stat_nm} 사용 가능"
        self._attr_unique_id = f"{stat_id}_summary"
        self._attr_icon = "mdi:ev-station"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
            name=self.stat_nm,
            manufacturer="환경부 공공데이터",
            model="EV Station"
        )

    @property
    def native_value(self):
        # 상태(stat)가 2(사용가능)인 개수 총합 계산[cite: 1]
        available = sum(1 for charger in self.coordinator.data.values() if str(charger.get("stat")) == "2")
        return available

    @property
    def extra_state_attributes(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        type_code = str(charger_data.get("chgerType", "00"))
        
        # 02(AC완속), 08(DC콤보 완속)은 완속으로 분류, 나머지는 급속으로 분류
        speed_type = "완속" if type_code in ["02", "08"] else "급속"
        if type_code == "00":
            speed_type = "알수없음"

        # 출력 용량 포맷팅 (빈 값이면 알수없음 처리)
        output_kw = charger_data.get("output", "")
        output_display = f"{output_kw} kW" if output_kw else "알수없음"

        return {
            "충전기_타입": TYPE_MAPPING.get(type_code, "알수없음"),
            "충전속도": speed_type,
            "출력용량": output_display,
            "충전방식": charger_data.get("method", "알수없음"), # 단독, 동시(공유) 표기
            "최종갱신일시": charger_data.get("statUpdDt", "알수없음")
        }


class ChargerPortSensor(CoordinatorEntity, SensorEntity):
    """개별 충전기 포트 센서"""

    def __init__(self, coordinator, stat_id, stat_nm, chger_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.stat_nm = stat_nm
        self.chger_id = chger_id
        self._attr_name = f"{stat_nm} 충전기 {chger_id}번"
        self._attr_unique_id = f"{stat_id}_charger_{chger_id}"

    @property
    def device_info(self):
        # StationSummarySensor와 동일한 식별자를 사용하여 하나의 기기 밑으로 종속시킴
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
        )

    @property
    def native_value(self):
        # 개별 충전기 상태값 가져오기 (예: "2")[cite: 1]
        charger_data = self.coordinator.data.get(self.chger_id, {})
        stat_code = str(charger_data.get("stat", "0"))
        # 코드를 사람이 읽기 쉬운 텍스트로 변환[cite: 1]
        return STAT_MAPPING.get(stat_code, "알수없음")

    @property
    def icon(self):
        # 충전 중(3)일 때 아이콘 변경[cite: 1]
        charger_data = self.coordinator.data.get(self.chger_id, {})
        if str(charger_data.get("stat")) == "3":
            return "mdi:ev-plug-type2"
        return "mdi:ev-plug-type2"

    @property
    def extra_state_attributes(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        type_code = str(charger_data.get("chgerType", "00"))
        
        return {
            "charger_type": TYPE_MAPPING.get(type_code, "알수없음"), #[cite: 1]
            "output_kw": charger_data.get("output", "알수없음"), #[cite: 1]
            "last_updated": charger_data.get("statUpdDt", "알수없음") #[cite: 1]
        }