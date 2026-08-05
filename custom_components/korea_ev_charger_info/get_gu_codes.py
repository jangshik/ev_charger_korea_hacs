import urllib.request
import urllib.parse
import json

# 여기에 디코딩된 원문 API 키를 넣으세요.
API_KEY = "wA5I6S9vDqVW9ePNhNmARX1IGf8V2PksCSQA5XoZkXJTTc1nl2Sh2ae6oAXrK8qYFrsFD25xTOoh7qVpyJJjUQ%3D%3D"



encoded_key = "wA5I6S9vDqVW9ePNhNmARX1IGf8V2PksCSQA5XoZkXJTTc1nl2Sh2ae6oAXrK8qYFrsFD25xTOoh7qVpyJJjUQ%3D%3D"
#urllib.parse.quote(API_KEY)


base_url = f"http://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList?ServiceKey={encoded_key}&type=json&numOfRows=1000&flag=Y"

gu_codes = {}
page = 1

print("5자리 구/군 단위 코드 추출을 시작합니다...")

while True:
    url = f"{base_url}&pageNo={page}"
    req = urllib.request.Request(url)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            stan_data = data.get("StanReginCd", [])
            if len(stan_data) < 2 or "row" not in stan_data[1]:
                break
                
            rows = stan_data[1]["row"]
            for row in rows:
                # 읍면동코드가 '000'인 경우만 필터링 (구/군 레벨)[cite: 1]
                if row.get("umd_cd") == "000":
                    sido = row.get("sido_cd", "") #[cite: 1]
                    sgg = row.get("sgg_cd", "") #[cite: 1]
                    name = row.get("locatadd_nm", "") #[cite: 1]
                    
                    # 시군구 코드가 존재하는 경우 5자리 코드 조합[cite: 1]
                    if sido and sgg and sgg != "000":
                        code_5digit = sido + sgg
                        gu_codes[code_5digit] = name
            
            total_count = int(stan_data[0]["head"][0]["totalCount"])
            if page * 1000 >= total_count:
                break
                
        page += 1
        
    except Exception as e:
        print(f"API 호출 중 에러 발생: {e}")
        break

# HA const.py에 바로 붙여넣기 좋게 파이썬 딕셔너리 포맷으로 텍스트 파일 저장
with open('gu_codes_dict.txt', 'w', encoding='utf-8') as f:
    f.write("REGION_CODES = {\n")
    # 코드를 기준으로 오름차순 정렬하여 저장
    for code, name in sorted(gu_codes.items()):
        f.write(f'    "{code}": "{name}",\n')
    f.write("}\n")

print(f"추출 완료! 전국 {len(gu_codes)}개의 5자리 지역 코드가 'gu_codes_dict.txt'에 깔끔하게 저장되었습니다.")
