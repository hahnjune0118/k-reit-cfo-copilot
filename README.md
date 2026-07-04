# K-REIT CFO Copilot

**K-REIT CFO Copilot: AI-powered decision intelligence for listed REIT CFOs, AMCs, and IR teams.**

현재 버전: **v02**

## Project Overview

K-REIT CFO Copilot은 상장 리츠 CFO, AMC, IR팀이 금리, 차입, 자산, 세금, 배당, 공시 품질 리스크를 하나의 Dashboard에서 진단하고, 시나리오 분석 결과를 CFO 보고 메모와 Investor Q&A로 전환하는 **client-facing AX prototype**입니다.

이 프로젝트는 회계 담당자를 위한 내부 자동화 도구가 아닙니다. CFO, AMC, IR팀이 경영 의사결정과 투자자 커뮤니케이션에 바로 사용할 수 있는 consulting-style decision intelligence platform을 지향합니다.

## Client Pain Point

상장 REIT 의사결정은 보통 DART 공시, IR 자료, 차입 스케줄, 자산관리 파일, 세무 검토, Excel 모델에 흩어져 있습니다. 이로 인해 다음 문제가 반복됩니다.

- 금리 변동과 차입 만기 리스크가 배당 지속 가능성과 분리되어 검토됩니다.
- 임대료, 자산가치, LTV, 세금 영향이 하나의 Scenario Engine에서 연결되지 않습니다.
- CFO 보고용 management narrative와 Investor Q&A가 매번 수작업으로 작성됩니다.
- 공시 품질과 Data Quality 이슈가 AI Readiness 진단으로 이어지지 못합니다.
- AMC의 자산 단위 리스크와 IR팀의 투자자 커뮤니케이션이 같은 데이터 기반으로 연결되지 않습니다.

## Target Users

- **CFO**: refinancing risk, dividend sustainability, tax-adjusted cash flow, LTV, 배당 정책을 한 화면에서 점검해야 하는 의사결정자
- **AMC**: 자산별 NOI, occupancy, WALE, tenant concentration, capex risk를 투자자 설명 가능한 형태로 정리해야 하는 운용 조직
- **IR팀**: 금리, 배당, 자산가치, 공시 품질 관련 질문에 일관된 Investor Q&A와 disclosure narrative가 필요한 커뮤니케이션 조직

## Solution Architecture

MVP는 `/data`의 mock REIT 데이터, `/modules`의 재사용 가능한 analytics 함수, `/pages`의 6개 Streamlit 화면으로 구성됩니다.

```text
k-reit-cfo-copilot/
  app.py
  VERSION.md
  CHANGELOG.md
  ROADMAP.md
  data/
    sample_reits.csv
    sample_assets.csv
    sample_debt.csv
    sample_disclosure_flags.csv
    sample_readiness.csv
  modules/
    data_loader.py
    scenario_engine.py
    risk_scoring.py
    memo_generator.py
    ui_components.py
  pages/
    1_고객_Pain_Point.py
    2_CFO_Executive_Dashboard.py
    3_Scenario_Engine.py
    4_자산_및_차입_리스크.py
    5_AI_Memo_Investor_QA.py
    6_데이터_품질_AI_Readiness.py
```

## Six Dashboard Modules

1. **고객 Pain Point**  
   CFO, AMC, IR팀의 실제 업무 pain point를 business risk와 Copilot response로 연결합니다.

2. **CFO Executive Dashboard**  
   refinancing risk, dividend coverage, tax-adjusted cash flow, AI Readiness, disclosure flags를 CFO 관점에서 요약합니다.

3. **Scenario Engine**  
   interest rate shock, rent change, asset value change, tax impact 슬라이더로 배당 지속 가능성, LTV, tax-adjusted cash flow 변화를 시뮬레이션합니다.

4. **자산 및 차입 리스크**  
   자산별 Risk Score, debt maturity wall, floating-rate exposure, LTV, disclosure flags를 함께 보여줍니다.

5. **AI Memo & Investor Q&A**  
   외부 LLM API 없이 rule-based 방식으로 CFO briefing memo와 Investor Q&A draft를 생성합니다.

6. **데이터 품질 및 AI Readiness**  
   Data Quality, KPI standardization, scenario capability, tax-finance integration, AI use case readiness를 진단합니다.

## Business Impact

- CFO가 금리, 차입, 자산, 세금, 배당 리스크를 하나의 Dashboard에서 빠르게 점검할 수 있습니다.
- AMC는 자산별 risk ranking을 투자자 설명 가능한 management narrative로 전환할 수 있습니다.
- IR팀은 반복되는 Investor Q&A에 대해 데이터 기반의 일관된 답변 초안을 만들 수 있습니다.
- Data Quality와 disclosure flags를 AI Readiness roadmap으로 연결할 수 있습니다.
- AX consulting 관점에서 진단, 시나리오, 보고, 커뮤니케이션, readiness까지 하나의 story로 제시할 수 있습니다.

## Tech Stack

- `streamlit`: client-facing Dashboard UI
- `pandas`: mock REIT 데이터 로딩 및 transformation
- `numpy`: Risk Score, scenario calculation, score clipping
- `plotly`: executive chart, waterfall, maturity wall, peer comparison

## Versioning

현재 릴리스는 **v02**입니다. 향후 feature update는 `v03`, `v04`, `v05` 형식으로 순차 증가해야 합니다.

버전이 변경될 때는 다음 파일과 앱 표시를 함께 업데이트합니다.

- `README.md`
- `VERSION.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- Streamlit sidebar version display

## Future Roadmap

- DART, 시장금리, 차입 스케줄, 자산관리, IR 자료 connector 연동
- AFFO, covenant headroom, hedge ratio, refinancing assumption 고도화
- 세무 로직 확장: 배당가능이익, 보유세, 거래세, withholding, taxable income bridge
- 승인 workflow 기반 AI Memo 및 Investor Q&A governance
- 공시 자료와 IR deck 기반 retrieval-augmented generation
- CFO, AMC, IR팀별 role-based view
- board memo, lender pack, investor FAQ export 기능

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
