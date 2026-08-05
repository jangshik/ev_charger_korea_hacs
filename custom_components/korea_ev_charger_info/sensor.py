"""Sensor platform for Korea EV Charger."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
    
    # 1. 통합 메인 요약 센서 (전체 사용가능 갯수)
    entities.append(StationSummarySensor(coordinator, stat_id))

    # 2. 💡 신규: 완속/급속 별 갯수 및 사용가능 센서 (4종)
    summary_types = ["slow_total", "fast_total", "slow_available", "fast_available"]
    for s_type in summary_types:
        entities.append(StationDetailSummarySensor(coordinator, stat_id, s_type))

    # 3. 각 개별 충전기 포트별 센서 생성
    if coordinator.data:
        for chger_id in coordinator.data:
            entities.append(ChargerPortSensor(coordinator, stat_id, chger_id))

    async_add_entities(entities)


class StationSummarySensor(CoordinatorEntity, SensorEntity):
    """충전소 전체 사용 가능한 충전기 수 (요약 메인 센서)"""

    def __init__(self, coordinator, stat_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        
        first_charger = next(iter(coordinator.data.values()), {}) if coordinator.data else {}
        self.busi_nm = first_charger.get("busiNm", "알수없음")
        self.stat_nm = first_charger.get("statNm", "알수없음")
        
        # 네이밍 룰 통일: 충전소명_사업자명_전체_사용가능
        self._attr_name = f"{self.stat_nm}_{self.busi_nm}_전체_사용가능"
        self._attr_unique_id = f"{stat_id}_summary_v2"
        self._attr_icon = "mdi:ev-station"
        
        self._attr_native_unit_of_measurement = "대"
        self._attr_state_class = SensorStateClass.MEASUREMENT

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
        if not self.coordinator.data:
            return 0
        return sum(1 for charger in self.coordinator.data.values() if str(charger.get("stat", "0")) == "2")


class StationDetailSummarySensor(CoordinatorEntity, SensorEntity):
    """💡 완속/급속 별 전체 및 사용가능 갯수 센서"""

    def __init__(self, coordinator, stat_id, sensor_type):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.sensor_type = sensor_type
        
        first_charger = next(iter(coordinator.data.values()), {}) if coordinator.data else {}
        self.busi_nm = first_charger.get("busiNm", "알수없음")
        self.stat_nm = first_charger.get("statNm", "알수없음")
        
        # 센서 타입에 따른 꼬리말 지정
        type_names = {
            "slow_total": "완속_전체",
            "fast_total": "급속_전체",
            "slow_available": "완속_사용가능",
            "fast_available": "급속_사용가능"
        }
        
        self._attr_name = f"{self.stat_nm}_{self.busi_nm}_{type_names[sensor_type]}"
        self._attr_unique_id = f"{stat_id}_{sensor_type}"
        
        # 가시성을 위해 사용가능 센서와 전체 갯수 센서의 아이콘을 구분
        if "available" in sensor_type:
            self._attr_icon = "mdi:check-circle-outline"
        else:
            self._attr_icon = "mdi:ev-station"
            
        self._attr_native_unit_of_measurement = "대"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return 0
            
        count = 0
        for charger in self.coordinator.data.values():
            chger_type = str(charger.get("chgerType", "00"))
            stat_code = str(charger.get("stat", "0"))
            
            # 02, 08은 완속, 나머지는 급속 / 2는 사용가능
            is_slow = chger_type in ["02", "08"]
            is_available = (stat_code == "2")
            
            # 요청된 센서 타입에 맞춰 카운팅
            if self.sensor_type == "slow_total" and is_slow:
                count += 1
            elif self.sensor_type == "fast_total" and not is_slow:
                count += 1
            elif self.sensor_type == "slow_available" and is_slow and is_available:
                count += 1
            elif self.sensor_type == "fast_available" and not is_slow and is_available:
                count += 1
                
        return count


class ChargerPortSensor(CoordinatorEntity, SensorEntity):
    """개별 충전기 포트 센서"""

    def __init__(self, coordinator, stat_id, chger_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.chger_id = chger_id
        
        charger_data = coordinator.data.get(chger_id, {})
        self.busi_nm = charger_data.get("busiNm", "알수없음")
        self.stat_nm = charger_data.get("statNm", "알수없음")
        
        type_code = str(charger_data.get("chgerType", "00"))
        self.speed_kr = "완속" if type_code in ["02", "08"] else "급속"
        self.speed_type = "slow" if type_code in ["02", "08"] else "fast"
        
        self._attr_name = f"{self.stat_nm}_{self.busi_nm}_{self.speed_kr}_{chger_id}"
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
            return "mdi:ev-plug-type2"
        return "mdi:ev-plug-type2"

    @property
    def extra_state_attributes(self):
        charger_data = self.coordinator.data.get(self.chger_id, {})
        type_code = str(charger_data.get("chgerType", "00"))
        
        output_kw = charger_data.get("output", "")
        output_display = f"{output_kw} kW" if output_kw else "알수없음"

        return {
            "충전기_타입": TYPE_MAPPING.get(type_code, "알수없음"),
            "충전속도": self.speed_kr,
            "출력용량": output_display,
            "충전방식": charger_data.get("method", "알수없음"),
            "마지막_충전시작일시": format_dt(charger_data.get("lastTsdt")),
            "마지막_충전종료일시": format_dt(charger_data.get("lastTedt")),
            "충전중_시작일시": format_dt(charger_data.get("nowTsdt")),
            "최종갱신일시": format_dt(charger_data.get("statUpdDt"))
        }