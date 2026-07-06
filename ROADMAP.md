# ROADMAP

## v10 완료

- Real API Mode를 responsible real-data insight layer로 강화했습니다.
- OpenDART Disclosure Monitor에서 최근 공시, 공시명, 접수일, 보고서 유형, 접수번호, 원문 링크, 정기공시 여부, freshness indicator를 표시합니다.
- ECOS Market Rate Panel에서 최신 시장금리, 기준일, 최근 추세, 데이터 출처 상태, rate shock basis를 표시합니다.
- Real API Mode manual scenario bridge에서 사용자 입력 기반 LTV, interest expense, dividend buffer, refinancing pressure를 계산합니다.
- Data Availability Matrix로 API 자동화 가능 영역과 manual validation 필요 영역을 구분했습니다.
- 실제 listed REIT에 대해 검증되지 않은 부정적 Risk Score, 투자 의견, 신용 판단을 생성하지 않도록 Real Mode를 제한했습니다.

## v11 후보

- OpenDART corp_code 자동 매핑 고도화
- OpenDART 공시 원문 링크 및 핵심 보고서 분류 정교화
- ECOS 기준금리, 국고채, 회사채 spread 등 market rate assumption library 확장
- Real API Mode에서 사용자 입력 validation 및 저장 구조 개선

## v12 후보

- KRX 상장 REIT 가격, 거래량, market cap data 연동
- 실제 공시 주석과 내부 treasury file을 결합한 debt maturity normalization
- FFO, AFFO, WALE, tenant concentration 수동 입력 template 정교화

## v13 후보

- Figma prototype 기반 UX 고도화
- Power BI dashboard 또는 executive reporting layer 확장
- Power Automate workflow 기반 memo review, approval, owner tracking

## 장기 후보

- OpenAI API-based memo generation
- retrieval-augmented Investor Q&A
- CFO, AMC, IR, Risk Management별 role-based Dashboard
- client-specific calibration workshop을 통한 Risk Score weighting 조정

## 보류 항목

- v10에서는 OpenAI API, KRX API, Figma, Power BI, Power Automate를 추가하지 않았습니다.
- Real API Mode는 모든 REIT metric을 자동화하지 않습니다. FFO, AFFO, WALE, tenant concentration, asset-level NOI, 차입 만기 구조, 세금효과는 내부 자료 또는 원문 공시 검증이 필요한 영역으로 유지합니다.
