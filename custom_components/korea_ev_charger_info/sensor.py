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
    
    # 1. 통합 메인 요약 센서 (맨 위: 전체)
    entities.append(StationSummarySensor(coordinator, stat_id))

    # 2~5. 요약 센서들 (급속전체 -> 급속사용가능 -> 완속전체 -> 완속사용가능)
    summary_types = ["fast_total", "fast_available", "slow_total", "slow_available"]
    for s_type in summary_types:
        entities.append(StationDetailSummarySensor(coordinator, stat_id, s_type))

    # 6. 급속 충전기들
    if coordinator.data:
        fast_chargers = [
            chger_id for chger_id, data in coordinator.data.items() 
            if str(data.get("chgerType", "00")) not in ["02", "08"]
        ]
        for chger_id in sorted(fast_chargers):
            entities.append(ChargerPortSensor(coordinator, stat_id, chger_id))

    # 7. 완속 충전기들
    if coordinator.data:
        slow_chargers = [
            chger_id for chger_id, data in coordinator.data.items() 
            if str(data.get("chgerType", "00")) in ["02", "08"]
        ]
        for chger_id in sorted(slow_chargers):
            entities.append(ChargerPortSensor(coordinator, stat_id, chger_id))

    async_add_entities(entities)


class StationSummarySensor(CoordinatorEntity, SensorEntity):
    """충전소 전체 사용 가능한 충전기 수"""

    def __init__(self, coordinator, stat_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        
        first_charger = next(iter(coordinator.data.values()), {}) if coordinator.data else {}
        self.busi_nm = first_charger.get("busiNm", "알수없음")
        self.stat_nm = first_charger.get("statNm", "알수없음")
        
        # 💡 HA 최신 네이밍 규칙 적용
        self._attr_has_entity_name = True
        self._attr_name = "전체_사용가능"
        self._attr_unique_id = f"{stat_id}_summary_v2"
        self._attr_icon = "mdi:ev-station"
        self._attr_native_unit_of_measurement = "대"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        # 💡 기기(Device)의 기본 이름을 설정합니다. (나중에 UI에서 변경 가능)
        return DeviceInfo(
            identifiers={(DOMAIN, self.stat_id)},
            name=f"{self.stat_nm} ({self.busi_nm})",
            manufacturer=self.busi_nm,
            model="EV Station"
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return 0
        return sum(1 for charger in self.coordinator.data.values() if str(charger.get("stat", "0")) == "2")


class StationDetailSummarySensor(CoordinatorEntity, SensorEntity):
    """완속/급속 별 갯수 센서"""

    def __init__(self, coordinator, stat_id, sensor_type):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.sensor_type = sensor_type
        
        type_names = {
            "fast_total": "급속_전체",
            "fast_available": "급속_사용가능",
            "slow_total": "완속_전체",
            "slow_available": "완속_사용가능"
        }
        
        self._attr_has_entity_name = True
        self._attr_name = type_names[sensor_type]
        self._attr_unique_id = f"{stat_id}_{sensor_type}"
            
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
            
            is_slow = chger_type in ["02", "08"]
            is_available = (stat_code == "2")
            
            if self.sensor_type == "slow_total" and is_slow:
                count += 1
            elif self.sensor_type == "fast_total" and not is_slow:
                count += 1
            elif self.sensor_type == "slow_available" and is_slow and is_available:
                count += 1
            elif self.sensor_type == "fast_available" and not is_slow and is_available:
                count += 1
                
        return count

    # 💡 새롭게 추가/변경된 아이콘 동적 할당 로직
    @property
    def icon(self):
        # 1. 사용 가능한 자리가 0개일 때는 경고등 아이콘 표출
        if "available" in self.sensor_type and self.native_value == 0:
            return "mdi:alert-circle-outline"
            
        # 2. 급속 아이콘 (전체: 꽉찬 번개 / 사용가능: 빈 번개)
        if self.sensor_type == "fast_total":
            return "mdi:lightning-bolt"
        elif self.sensor_type == "fast_available":
            return "mdi:lightning-bolt-outline"
            
        # 3. 완속 아이콘 (전체: 꽉찬 플러그 / 사용가능: 빈 플러그)
        elif self.sensor_type == "slow_total":
            return "mdi:power-plug"
        elif self.sensor_type == "slow_available":
            return "mdi:power-plug-outline"
            
        return "mdi:ev-station"


class ChargerPortSensor(CoordinatorEntity, SensorEntity):
    """개별 충전기 포트 센서"""

    def __init__(self, coordinator, stat_id, chger_id):
        super().__init__(coordinator)
        self.stat_id = stat_id
        self.chger_id = chger_id
        
        charger_data = coordinator.data.get(chger_id, {})
        type_code = str(charger_data.get("chgerType", "00"))
        
        self.speed_kr = "완속" if type_code in ["02", "08"] else "급속"
        self.speed_type = "slow" if type_code in ["02", "08"] else "fast"
        
        self._attr_has_entity_name = True
        self._attr_name = f"{self.speed_kr}_{chger_id}"
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
        stat_code = str(charger_data.get("stat", "0"))
        
        # 급속 충전기 (CCS1 등)
        if self.speed_type == "fast":
            if stat_code == "3":  # 충전 중: 꽉 찬 전용 플러그
                return "mdi:ev-plug-ccs1"
            elif stat_code == "2":  # 사용 가능: 빈 번개 모양 (대기 중)
                return "mdi:lightning-bolt-outline"
            else:  # 점검중, 통신이상 등: 경고 모양
                return "mdi:alert-circle-outline"
                
        # 완속 충전기 (테슬라 / AC완속 등)
        else:
            if stat_code == "3":  # 충전 중: 꽉 찬 전용 플러그
                return "mdi:ev-plug-tesla"
            elif stat_code == "2":  # 사용 가능: 빈 일반 플러그 (대기 중)
                return "mdi:power-plug-outline"
            else:  # 점검중, 통신이상 등: 경고 모양
                return "mdi:alert-circle-outline"

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