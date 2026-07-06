# ROADMAP

## v12 완료

- Real API Mode를 기본 흐름으로 전환했습니다.
- Demo / Sample Mode는 fictional sample data 기반 데모로 명확히 구분했습니다.
- 모든 real metric에 source/confidence/as_of/calculation_method/warning metadata를 붙이는 `source_confidence` layer를 추가했습니다.
- OpenDART account mapper, OpenDART client wrapper, OpenDART parser wrapper, market data client wrapper를 추가했습니다.
- Real REIT dashboard model과 8-component risk model을 추가했습니다.
- CFO Executive Dashboard, Scenario Engine, Asset & Debt Risk, AI Memo & Investor Q&A, Data Quality & AI Readiness page를 v12 Real Mode 중심으로 개선했습니다.
- API key가 없을 때 company-specific financials를 sample 값이나 High confidence 값으로 채우지 않도록 유지했습니다.

## v12에서 의도적으로 하지 않은 일

- OpenAI API 또는 외부 LLM API 연동
- Power BI dashboard
- Power Automate workflow
- Figma prototype
- 실제 고객 내부자료 연동
- 실제 투자 의견, 신용 판단, 부정적 리스크 평가 제공

## 단기 Roadmap

- OpenDART financial statement account mapping alias 추가
- OpenDART report parser의 debt note, dividend, portfolio asset table extraction 정확도 개선
- ECOS treasury / corporate bond series mapping 확정
- KRX 또는 안정적인 market data source 연결
- source inventory와 collected metrics export 기능

## 중기 Roadmap

- FFO / AFFO bridge validation workflow
- WALE, tenant concentration, asset-level NOI parser 및 manual validation workflow
- debt maturity schedule parser 고도화
- peer comparison 자동 수집 범위 확대
- board memo / IR Q&A template governance

## 장기 AX 전환 과제

- 고객 내부 treasury, accounting, asset management data 연결
- approval workflow와 disclosure workflow 연계
- Power BI dashboard
- Power Automate workflow
- Figma prototype
- OpenAI API-based memo generation
- CFO cockpit 운영모델 및 KPI dictionary 표준화

