"""Sensor platform for Korea EV Charger."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_STAT_ID, STAT_MAPPING, TYPE_MAPPING

def format_dt(dt_str):
    """14자리 시간 문자열(YYYYMMDDHHMMSS)을 보기 좋게 변환합니다."""
    if not dt_str or len(str(dt_str)) != 14:
        return dt_str
    dt = str(dt_str)
    return f"{dt[:4]}-{dt[4:6]}-{dt[6:8]} {dt[8:10]}:{dt[10:12]}:{dt[12:14]}"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    stat_id = entry.data[CONF_STAT_ID]

    entities = []
    
    # 1. 충전소 통합 상태 센서 (요약 센서)
    entities.append(StationSummarySensor(coordinator, stat_id))

    # 2. 각 개별 충전기 포트별 센서 생성
    if coordinator.data:
        for chger_id in coordinator.data:
            entities.append(ChargerPortSensor(coordinator, stat_id, chger_id))

    async_add_entities(entities)


class StationSummarySensor(CoordinatorEntity, SensorEntity):
    """충전소 전체 사용 가능한 충전기 수 (요약 메인 센서)"""

    def __init__(self, coordinator, stat_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        
        # API에서 실제 사업자명과 충전소명을 동적으로 가져옵니다.
        first_charger = next(iter(coordinator.data.values()), {}) if coordinator.data else {}
        self.busi_nm = first_charger.get("busiNm", "알수없음")
        self.stat_nm = first_charger.get("statNm", "알수없음")
        
        # 엔티티 이름 룰 적용
        self._attr_name = f"{self.busi_nm}_{self.stat_nm}_요약"
        self._attr_unique_id = f"{stat_id}_summary"
        self._attr_icon = "mdi:ev-station"
        
        # 💡 '사용할 수 없음' 에러 방지를 위해 단위를 명시합니다.
        self._attr_native_unit_of_measurement = "대"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
            name=self.stat_nm,
            manufacturer=self.busi_nm,
            model="EV Station"
        )

    @property
    def native_value(self):
        # 데이터가 없을 경우 안전하게 0 반환
        if not self.coordinator.data:
            return 0
        # 사용가능(2) 상태인 충전기 개수 카운트
        return sum(1 for charger in self.coordinator.data.values() if str(charger.get("stat")) == "2")

    @property
    def extra_state_attributes(self):
        total = len(self.coordinator.data) if self.coordinator.data else 0
        return {
            "전체_충전기_수": total,
            "충전소ID": self.stat_id
        }


class ChargerPortSensor(CoordinatorEntity, SensorEntity):
    """개별 충전기 포트 센서"""

    def __init__(self, coordinator, stat_id, chger_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.chger_id = chger_id
        
        # 초기화 시 API 데이터 추출
        charger_data = coordinator.data.get(chger_id, {})
        self.busi_nm = charger_data.get("busiNm", "알수없음")
        self.stat_nm = charger_data.get("statNm", "알수없음")
        
        # 완속/급속 판단 (02, 08은 완속, 나머지는 급속)
        type_code = str(charger_data.get("chgerType", "00"))
        self.speed_type = "slow" if type_code in ["02", "08"] else "fast"
        
        # 💡 사용자 요청 네이밍 룰 반영: 사업자명_충전소명_fast/slow_충전기ID
        self._attr_name = f"{self.busi_nm}_{self.stat_nm}_{self.speed_type}_{chger_id}"
        self._attr_unique_id = f"{stat_id}_{chger_id}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
        )

    @property
    def native_value(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        stat_code = str(charger_data.get("stat", "0"))
        return STAT_MAPPING.get(stat_code, "알수없음")

    @property
    def icon(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        if str(charger_data.get("stat")) == "3":
            return "mdi:ev-plug-type2" # 충전중
        return "mdi:ev-plug-type2"

    @property
    def extra_state_attributes(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        type_code = str(charger_data.get("chgerType", "00"))
        
        speed_kr = "완속" if self.speed_type == "slow" else "급속"
        output_kw = charger_data.get("output", "")
        output_display = f"{output_kw} kW" if output_kw else "알수없음"

        # 💡 요청하신 모든 날짜/시간 정보를 보기 좋게 포맷팅하여 속성에 추가
        return {
            "충전기_타입": TYPE_MAPPING.get(type_code, "알수없음"),
            "충전속도": speed_kr,
            "출력용량": output_display,
            "충전방식": charger_data.get("method", "알수없음"),
            "마지막_충전시작일시": format_dt(charger_data.get("lastTsdt")),
            "마지막_충전종료일시": format_dt(charger_data.get("lastTedt")),
            "충전중_시작일시": format_dt(charger_data.get("nowTsdt")),
            "최종갱신일시": format_dt(charger_data.get("statUpdDt"))
        }