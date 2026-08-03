"""Constants for the Korea EV Charger integration."""
from datetime import timedelta

DOMAIN = "korea_ev"
CONF_API_KEY = "api_key"
CONF_ZCODE = "zscode"
CONF_KEYWORD = "search_keyword"
CONF_STAT_ID = "stat_id"
CONF_STAT_NM = "stat_nm"

# 공공데이터 API 제한 (일일 1000회) 고려 3분 주기
UPDATE_INTERVAL = timedelta(minutes=3)

# 상태 코드 매핑[cite: 1]
STAT_MAPPING = {
    "0": "알수없음",
    "1": "통신이상",
    "2": "사용가능",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "6": "예약중",
    "9": "상태미확인"
}

# 충전기 타입 매핑[cite: 1]
TYPE_MAPPING = {
    "01": "DC차데모",
    "02": "AC완속",
    "03": "DC차데모+AC3상",
    "04": "DC콤보",
    "05": "DC차데모+DC콤보",
    "06": "DC차데모+AC3상+DC콤보",
    "07": "AC3상",
    "08": "DC콤보(완속)",
    "09": "NACS",
    "10": "DC콤보+NACS",
    "11": "DC콤보2(버스전용)"
}