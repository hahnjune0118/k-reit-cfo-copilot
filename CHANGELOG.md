# CHANGELOG

## v04 - CFO Executive Dashboard Attention Allocation

- VERSION.md의 current version을 v04로 업데이트했습니다.
- Streamlit sidebar version display가 v04를 표시하도록 업데이트했습니다.
- CFO Executive Dashboard를 attention allocation tool로 강화했습니다.
- Overall Risk Score 계산을 추가했습니다.
- Refinancing Risk, Dividend Sustainability, Asset Risk, Disclosure Quality, AI Readiness category별 Risk Score와 label을 추가했습니다.
- Low, Watch, High color-coded risk label을 추가했습니다.
- Top 3 CFO Alerts를 추가했습니다.
- “CFO가 오늘 가장 먼저 확인해야 할 리스크”, “왜 이 리스크가 중요한가”, “권고 액션” 설명 박스를 추가했습니다.
- Risk score by category chart를 추가했습니다.
- Dividend sustainability scenario comparison chart를 추가했습니다.
- README.md에 CFO Executive Dashboard의 business purpose를 추가했습니다.

## v03 - Scenario Engine Decision Support

- VERSION.md의 current version을 v03으로 업데이트했습니다.
- Streamlit sidebar version display가 v03을 표시하도록 업데이트했습니다.
- Scenario Engine을 CFO-level decision support 화면으로 확장했습니다.
- 금리 충격, 임대료 변화율, 자산가치 변화율, 세금효과 반영 여부 slider/input을 v03 요구 범위에 맞게 조정했습니다.
- sample REIT data 기반으로 Scenario-adjusted NOI, interest expense impact, FFO estimate, AFFO estimate, LTV change, dividend buffer, refinancing risk level을 계산하도록 개선했습니다.
- scenario summary table을 추가했습니다.
- Plotly chart를 추가해 dividend buffer impact와 LTV impact를 시각화했습니다.
- CFO interpretation box를 추가했습니다.
- README.md에 Scenario Engine의 business purpose와 계산 logic을 추가했습니다.

## v02 - Korean-First Portfolio Release

- README.md를 Korean-first portfolio project 스타일로 재작성했습니다.
- Streamlit landing page와 6개 page의 title, caption, table label, chart label, description을 Korean-first 문구로 전환했습니다.
- CFO, AMC, IR팀을 위한 client-facing AX prototype positioning을 명확히 했습니다.
- VERSION.md, CHANGELOG.md, ROADMAP.md를 추가했습니다.
- 앱 sidebar version display를 v02로 업데이트하고 VERSION.md 기반으로 관리하도록 정리했습니다.

## v01 - Initial MVP

- Streamlit 기반 6-page MVP를 구성했습니다.
- mock Korean REIT data, scenario sliders, refinancing risk, dividend sustainability, tax-adjusted cash flow, asset risk ranking, disclosure flags, AI Readiness score를 구현했습니다.
- rule-based CFO memo 및 Investor Q&A draft generator를 구현했습니다.
