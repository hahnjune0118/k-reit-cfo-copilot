# CHANGELOG

## v08 - External API Data Layer

- VERSION.md의 current version을 v08로 업데이트했습니다.
- Streamlit sidebar version display가 v08을 표시하도록 fallback 값을 업데이트했습니다.
- `modules/api_clients/` 폴더를 추가했습니다.
- OpenDART API client를 추가했습니다: `fetch_corp_code_zip`, `load_corp_codes`, `find_corp_by_name`, `fetch_disclosure_list`.
- ECOS API client를 추가했습니다: `fetch_ecos_stat`, `fetch_interest_rate_series`.
- API key는 Streamlit secrets를 먼저 확인하고, 없으면 `.env`에서 읽도록 `config.py`를 추가했습니다.
- API key가 없거나 API 호출이 실패해도 sample/mock data로 fallback하도록 설계했습니다.
- `data_loader.py`에 `load_reit_master_data`, `load_market_rate_data`, `load_disclosure_data`를 추가했습니다.
- Scenario Engine이 ECOS 또는 sample market rate를 base interest rate assumption으로 사용하도록 업데이트했습니다.
- Data Quality & AI Readiness page에 External Data Connection section을 추가했습니다.
- README.md에 “v08 External API Data Layer” section을 추가하고 OpenDART, ECOS, KRX roadmap, API key management, fallback design을 설명했습니다.
- Streamlit Cloud import 안정성을 위해 `modules/__init__.py`를 추가하고, `data_loader.py`가 API client import 실패 시에도 sample data fallback으로 동작하도록 lazy import wrapper를 적용했습니다.
- `reit_options()`와 `reit_id_from_name(name)` wrapper compatibility를 추가해 기존 page import가 깨지지 않도록 했습니다.
- OpenAI 또는 외부 LLM API는 추가하지 않았습니다.

## v07 - Portfolio Submission Polish for Samil PwC AX Node

- VERSION.md의 current version을 v07로 업데이트했습니다.
- Streamlit sidebar version display가 VERSION.md를 통해 v07을 표시하도록 fallback 값을 업데이트했습니다.
- README.md를 Samil PwC AX Node 포트폴리오 제출용으로 간결하게 재구성했습니다.
- README.md 구조를 프로젝트 개요, 고객 Pain Point, Target Users, Solution Architecture, 6개 Dashboard 구성, Business Impact, Tech Stack, Version History, Future Roadmap 중심으로 정리했습니다.
- README.md에 Mermaid architecture diagram을 추가했습니다.
- client-facing AX prototype positioning을 강화하고, 내부 회계 자동화 도구가 아니라는 설명을 별도 section으로 추가했습니다.
- 현재 데이터는 mock/sample data이며 외부 API 연동은 future roadmap이라는 점을 명확히 했습니다.
- Future Roadmap에 DART / ECOS / KRX API, Figma prototype, Power BI dashboard, Power Automate workflow, OpenAI API-based memo generation을 추가했습니다.

## v06 - Data Quality & AI Readiness AX Diagnostic

- Data Quality & AI Readiness page를 AX consulting diagnostic module로 강화했습니다.
- Data Quality Flags를 추가했습니다: Missing data, Inconsistent values, Unusual movement, Manual review required.
- AI Readiness Score dimensions를 가중치 기반으로 계산하도록 확장했습니다.
- 평가 dimension을 Data Availability, Data Consistency, KPI Standardization, Scenario Capability, Tax-Finance Integration, AI Use Case Readiness로 정리했습니다.
- Weighted AI Readiness Score와 Strong, Moderate, Needs Improvement 해석 로직을 추가했습니다.
- AI readiness by dimension Plotly chart와 peer comparison chart를 추가했습니다.
- 단기 개선 과제, 중기 개선 과제, 장기 AX 전환 과제로 구성된 improvement roadmap을 추가했습니다.
- 외부 LLM API, Figma, Power BI, Power Automate는 추가하지 않았습니다.

## v05 - AI Memo & Investor Q&A Narrative Generator

- AI Memo & Investor Q&A page를 management narrative generator로 강화했습니다.
- Scenario Engine output과 CFO Dashboard risk input을 rule-based logic으로 연결해 CFO Briefing Memo를 생성하도록 개선했습니다.
- CFO Briefing Memo section을 추가했습니다: 핵심 요약, 주요 리스크, 배당가능성 영향, 리파이낸싱 영향, 세금효과 고려사항, CFO 권고 액션.
- Investor Q&A Draft section을 추가했습니다: 예상 질문, 답변 초안, 커뮤니케이션 유의사항.
- memo focus 선택지를 추가했습니다: 배당 안정성, 리파이낸싱 리스크, 자산가치 하락, 임차인 리스크, 공시 품질.
- 생성된 memo와 Investor Q&A를 Markdown 또는 plain text로 다운로드할 수 있도록 버튼을 추가했습니다.
- 외부 LLM API는 추가하지 않았습니다.

## v04 - CFO Executive Dashboard Attention Allocation

- CFO Executive Dashboard를 attention allocation tool로 강화했습니다.
- Overall Risk Score 계산을 추가했습니다.
- Refinancing Risk, Dividend Sustainability, Asset Risk, Disclosure Quality, AI Readiness category별 Risk Score와 label을 추가했습니다.
- Low, Watch, High color-coded risk label을 추가했습니다.
- Top 3 CFO Alerts를 추가했습니다.
- “CFO가 오늘 가장 먼저 확인해야 할 리스크”, “왜 이 리스크가 중요한가”, “권고 액션” 설명 박스를 추가했습니다.
- Risk score by category chart와 Dividend Sustainability scenario comparison chart를 추가했습니다.

## v03 - Scenario Engine Decision Support

- Scenario Engine을 CFO-level decision support 화면으로 확장했습니다.
- 금리 충격, 임대료 변화율, 자산가치 변화율, 세금효과 반영 여부 slider를 강화했습니다.
- Scenario-adjusted NOI, interest expense impact, FFO estimate, AFFO estimate, LTV change, dividend buffer, refinancing risk level을 계산하도록 개선했습니다.
- scenario summary table, dividend buffer impact chart, LTV impact chart, CFO interpretation box를 추가했습니다.

## v02 - Korean-First Portfolio Release

- README.md를 Korean-first portfolio project 스타일로 재작성했습니다.
- Streamlit landing page와 6개 page의 title, caption, table label, chart label, description을 Korean-first 문구로 전환했습니다.
- CFO, AMC, IR팀을 위한 client-facing AX prototype positioning을 명확히 했습니다.
- VERSION.md, CHANGELOG.md, ROADMAP.md를 추가 또는 정비했습니다.

## v01 - Initial MVP

- Streamlit 기반 6-page MVP를 구성했습니다.
- mock Korean REIT data를 `/data` 폴더에 추가했습니다.
- reusable functions를 `/modules` 폴더에 구성했습니다.
- scenario sliders, refinancing risk, dividend sustainability, tax-adjusted cash flow, asset risk ranking, disclosure flags, AI Readiness score를 구현했습니다.
- rule-based CFO memo와 Investor Q&A draft generator를 구현했습니다.
