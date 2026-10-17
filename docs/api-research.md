# 공식 API 조사 기록

조사일: 2026-10-17 (Asia/Seoul)

## KOPIS

- 공식 안내: https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00077
- 개발가이드: https://kopis.or.kr/upload/openApi/공연예술통합전산망OpenAPI개발가이드.pdf
- 인증키가 필수이며 1인당 1개, 타인 양도·공유가 금지된다.
- 서비스에 KOPIS 기반임을 표시해야 한다. 권장 출처 문구는 `출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)`이다.
- 공연 목록: `GET /openApi/restful/pblprfr`, XML 응답, 페이지 최대 100건, 검색 기간 최대 31일.
- 서울 시도 코드는 `11`; 주요 목록 필드는 `mt20id`, `prfnm`, `prfpdfrom`, `prfpdto`, `fcltynm`, `poster`, `genrenm`, `prfstate`, `openrun`이다.
- 상세: `GET /openApi/restful/pblprfr/{mt20id}`. 가격(`pcseguidance`), 공연시간, 주소 등은 상세에서 보강한다.
- 공식 페이지는 키별 호출 제한이 있을 수 있다고 명시하나 공개 안내 화면에서 고정 일일 한도를 제시하지 않는다. 발급 메일/개발가이드의 해당 키 조건을 운영 전에 확인한다.

## 문화포털 / 문화공공데이터광장

- 공식 안내: https://www.culture.go.kr/data/contest/info.do
- 이번 1차 연동 상품: 전시정보(통합), 공식 상세 https://www.culture.go.kr/data/openapi/openapiView.do?id=598
- 요청 URL: `https://api.kcisa.kr/openapi/API_CCA_145/request`
- 요청 변수: `serviceKey`, `numOfRows`, `pageNo`; JSON 응답의 성공 코드는 `0000`이다.
- 2026-10-17 실측 전체 건수는 9,648건이었다. 첫 100건 기준 제목 100%, 기간 84%, 장소 78%,
  요금 10%, 원문 URL 100%였다. 구조화된 지역 필드는 비어 있어 장소·기관명으로 서울을 판정한다.
- 문화포털은 기관 데이터를 연계한 공연정보(통합)와 전시정보(통합)를 제공한다.
- 통합 모델은 제목, 기간, 시간, 장소, 관람/공연시간, 요금·할인 등을 포함한 24개 공통 메타데이터를 표준화한다.
- 기관 원문 저작권 때문에 일부 콘텐츠 제공이 제한될 수 있으며, 저작권 문의는 각 제공기관에 해야 한다.
- 구현은 `TITLE`, `PERIOD`, `EVENT_SITE`, `CHARGE`, `URL`, `DESCRIPTION`, `LOCAL_ID`,
  `CNTC_INSTT_NM`을 사용하며 원본 응답도 함께 보존한다.
- 이미지 URL은 MVP에서 저장하지 않는 것이 기본이며, 명세상 재사용 허용이 확인된 출처만 별도 활성화한다.

## 서울 열린데이터광장(보완 후보)

- 이용 안내: https://data.seoul.go.kr/together/guide/useGuide.do
- 한 번에 최대 1,000건을 요청하며 서비스별 제한은 데이터셋 메타정보에서 확인한다.
- 서울시 문화행사 정보는 KOPIS/문화포털 누락률 분석 후에만 추가한다.

## 2차 연동 보류: 수업 final project API

- 후보: 공공데이터포털 `한국문화정보원_한눈에보는문화정보조회서비스`
- 공식 문서: https://www.data.go.kr/data/15138937/openapi.do
- 수업 프로젝트에서 사용한 계열은 `apis.data.go.kr/B553457/cultureinfo`의 XML API이며 현재
  문화공공데이터광장 전시정보(통합) 키와 인증 체계가 다르다.
- 서울·기간·분야 조건 조회가 가능해 지역 판별과 누락 보완에 유리하다.
- 1차 서비스가 안정화되고 누락률을 확인한 뒤 별도 키를 신청해 추가한다.

## 라이선스 운영 원칙

`event_sources`에 제공기관, 원문 URL, API 문서 URL, 출처 표시문, 라이선스 메모, 마지막 확인 시각을 저장한다. 원문 링크와 데이터 갱신 시각은 상세 화면에 표시한다. 포스터는 URL이 응답에 있어도 재사용 허용을 별도로 확인하기 전에는 노출하지 않는다.

