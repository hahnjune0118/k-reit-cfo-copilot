# ROADMAP

## v11.1 완료

- Real API Mode에 automated Real Data Pipeline을 추가했습니다.
- OpenDART 재무제표 API, OpenDART 공시 목록, 공시 원문 parser, ECOS/macro layer, KRX/public market data attempt를 하나의 data bundle로 통합했습니다.
- 모든 real metric에 source와 confidence를 부여했습니다.
- 사용자 입력은 최초 산출값이 아니라 자동 수집 후 보완값으로 재정의했습니다.
- Real API Risk Score는 최소 4개 category가 확보될 때만 계산하도록 threshold를 적용했습니다.
- 차입 만기 구조는 단기차입금 또는 유동부채 기반 proxy를 먼저 표시하고, 약정별 만기는 manual validation 대상으로 분리했습니다.

## v11 완료

- Real API Mode를 raw API 조회 중심에서 CFO-useful analysis mode로 확장했습니다.
- 금액 표기를 조 / 억 / 만 원으로 통일했습니다.
- Real REIT selector를 Data Mode 바로 아래로 이동하고 ticker/corp_code는 기본 UI에서 숨겼습니다.
- ECOS 금리 화면을 요약형으로 단순화했습니다.
- BOK/ECOS actual rate와 KDI/IMF/OECD-style local outlook assumption, credit/refinancing spread assumption을 결합하는 macro assumption layer를 추가했습니다.
- Real API Mode risk indicators, CFO alerts, debt maturity wall, scenario outputs, data confidence report를 추가했습니다.
- 미확보 metric은 데이터 미확보, 사용자 입력 필요, manual validation 필요로 표시했습니다. v11.1에서는 자동 수집 시도 후 미확보로 문구와 로직을 개선했습니다.

## v10 완료

- Real API Mode를 responsible real-data insight layer로 강화했습니다.
- OpenDART Disclosure Monitor에서 최근 공시, 공시명, 접수일, 보고서 유형, 접수번호, 원문 링크, 정기공시 여부, freshness indicator를 표시합니다.
- ECOS Market Rate Panel에서 최신 시장금리, 기준일, 최근 추세, 데이터 출처 상태, rate shock basis를 표시합니다.
- Real API Mode manual scenario bridge에서 사용자 입력 기반 LTV, interest expense, dividend buffer, refinancing pressure를 계산합니다.
- Data Availability Matrix로 API 자동화 가능 영역과 manual validation 필요 영역을 구분했습니다.
- 실제 listed REIT에 대해 검증되지 않은 부정적 Risk Score, 투자 의견, 신용 판단을 생성하지 않도록 Real Mode를 제한했습니다.

## v12 후보

- OpenDART corp_code 자동 매핑 고도화
- OpenDART 공시 원문 parser의 table extraction 고도화
- Real API Mode에서 source/confidence badge UI 정교화
- Real API Mode에서 사용자 보완값 validation 및 저장 구조 개선

## v13 후보

- KRX 공식 API 또는 안정적인 market data provider 연동
- 실제 공시 주석과 내부 treasury file을 결합한 debt maturity normalization
- FFO, AFFO, WALE, tenant concentration 수동 입력 template 정교화

## v14 후보

- Figma prototype 기반 UX 고도화
- Power BI dashboard 또는 executive reporting layer 확장
- Power Automate workflow 기반 memo review, approval, owner tracking

## 장기 후보

- OpenAI API-based memo generation
- retrieval-augmented Investor Q&A
- CFO, AMC, IR, Risk Management별 role-based Dashboard
- client-specific calibration workshop을 통한 Risk Score weighting 조정

## 보류 항목

- v11에서는 OpenAI API, KRX API, Figma, Power BI, Power Automate를 추가하지 않았습니다.
- Real API Mode는 모든 REIT metric을 자동화하지 않습니다. FFO, AFFO, WALE, tenant concentration, asset-level NOI, 차입 만기 구조, 세금효과는 내부 자료 또는 원문 공시 검증이 필요한 영역으로 유지합니다.
