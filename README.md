# K-REIT CFO Copilot

**K-REIT CFO Copilot: AI-powered decision intelligence for listed REIT CFOs, AMCs, and IR teams.**

현재 버전: **v04**

## Project Overview

K-REIT CFO Copilot은 상장 REIT CFO, AMC, IR팀이 금리, 차입, 자산, 세금, 배당, 공시 품질 리스크를 하나의 Dashboard에서 진단하고, Scenario Engine 결과를 CFO 보고 메모와 Investor Q&A로 전환하는 **client-facing AX prototype**입니다.

이 프로젝트는 회계 담당자를 위한 내부 자동화 도구가 아닙니다. CFO가 오늘 어디에 attention을 먼저 배분해야 하는지 판단하도록 돕는 consulting-style decision intelligence platform입니다.

## Client Pain Point

상장 REIT 의사결정은 DART 공시, IR 자료, 차입 스케줄, 자산관리 파일, 세무 검토, Excel 모델에 흩어져 있습니다.

- refinancing risk와 dividend sustainability가 분리되어 검토됩니다.
- asset risk, disclosure quality, AI Readiness가 CFO attention allocation으로 연결되지 않습니다.
- CFO Dashboard가 데이터를 보여주기만 하고 “오늘 무엇을 먼저 봐야 하는지” 알려주지 못합니다.
- Investor Q&A와 management narrative가 정량 signal과 연결되지 않습니다.

## Target Users

- **CFO**: refinancing, dividend, asset, disclosure, AI Readiness 중 어디를 먼저 확인해야 하는지 판단해야 하는 의사결정자
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
   v04에서는 Dashboard를 attention allocation tool로 강화했습니다. Overall Risk Score와 5개 category Risk Score를 계산하고 Top 3 CFO Alerts를 제시합니다.

   리스크 category:
   - Refinancing Risk
   - Dividend Sustainability
   - Asset Risk
   - Disclosure Quality
   - AI Readiness

3. **Scenario Engine**  
   금리 충격, 임대료 변화율, 자산가치 변화율, 세금효과 반영 여부를 기반으로 Scenario-adjusted NOI, FFO, AFFO, LTV change, dividend buffer, refinancing risk level을 계산합니다.

4. **자산 및 차입 리스크**  
   자산별 Risk Score, debt maturity wall, floating-rate exposure, LTV, disclosure flags를 함께 보여줍니다.

5. **AI Memo & Investor Q&A**  
   외부 LLM API 없이 rule-based 방식으로 CFO briefing memo와 Investor Q&A draft를 생성합니다.

6. **데이터 품질 및 AI Readiness**  
   Data Quality, KPI standardization, scenario capability, tax-finance integration, AI use case readiness를 진단합니다.

## CFO Executive Dashboard v04

v04 Dashboard의 business purpose는 단순한 data display가 아닙니다. CFO가 다음 질문에 답할 수 있도록 attention allocation을 지원합니다.

> CFO가 오늘 가장 먼저 확인해야 할 리스크는 무엇인가?

Dashboard는 다음 signal을 계산합니다.

- **Overall Risk Score**: category별 Risk Score의 가중 평균
- **Refinancing Risk**: near-term maturity, floating-rate exposure, LTV, interest burden 기반
- **Dividend Sustainability**: dividend coverage와 dividend buffer 기반
- **Asset Risk**: occupancy, WALE, tenant concentration, capex risk 기반
- **Disclosure Quality**: open disclosure flag 및 high-severity flag 기반
- **AI Readiness**: Data Quality 및 KPI standardization readiness 기반

각 risk는 `Low`, `Watch`, `High` label로 표시되며, Top 3 CFO Alerts에는 다음 설명이 포함됩니다.

- CFO가 오늘 가장 먼저 확인해야 할 리스크
- 왜 이 리스크가 중요한가
- 권고 액션

## Business Impact

- CFO가 refinancing, dividend, asset, disclosure, AI Readiness 중 가장 먼저 볼 영역을 빠르게 판단할 수 있습니다.
- AMC는 asset Risk Score와 CFO attention signal을 연결해 더 설득력 있는 management narrative를 만들 수 있습니다.
- IR팀은 반복되는 Investor Q&A에 대해 Dashboard signal 기반의 일관된 답변 초안을 만들 수 있습니다.
- Data Quality와 disclosure flags를 AI Readiness roadmap으로 연결할 수 있습니다.

## Tech Stack

- `streamlit`: client-facing Dashboard UI
- `pandas`: mock REIT 데이터 로딩 및 transformation
- `numpy`: Risk Score, scenario calculation, score clipping
- `plotly`: executive chart, waterfall, maturity wall, peer comparison

## Versioning

현재 릴리스는 **v04**입니다. 향후 feature update는 `v05`, `v06`, `v07` 형식으로 순차 증가해야 합니다.

버전이 변경될 때는 다음 파일과 앱 표시를 함께 업데이트합니다.

- `README.md`
- `VERSION.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- Streamlit sidebar version display

## Future Roadmap

- CFO Alert와 AI Memo 자동 연결
- covenant headroom, hedge ratio, refinancing assumption 추가
- DART, 시장금리, 차입 스케줄, 자산관리, IR 자료 connector 연동
- CFO, AMC, IR팀별 role-based Dashboard

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
