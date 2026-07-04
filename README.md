# K-REIT CFO Copilot

**K-REIT CFO Copilot: AI-powered decision intelligence for listed REIT CFOs, AMCs, and IR teams.**

## Project Overview

This Streamlit MVP is a client-facing AX consulting prototype for listed Korean REIT CFOs, AMCs, IR teams, and risk management teams. It is designed to look and feel like a decision intelligence platform, not an internal accounting automation tool.

The product vision is to help leadership teams move from fragmented financial and operating data to scenario-based decision support, management narrative generation, investor communication, disclosure quality improvement, and AX readiness diagnostics.

## Customer Pain Point

Listed Korean REIT CFOs, AMCs, IR teams, and risk management teams need to explain dividend sustainability, refinancing exposure, asset risk, tax impact, and disclosure quality under changing market conditions. In practice, the inputs often live across DART disclosures, IR decks, lender workbooks, valuation files, tax schedules, and manually maintained Excel models.

That fragmentation creates several business problems:

- Refinancing risk is not always connected to dividend guidance.
- Rent, valuation, and interest-rate sensitivities are analyzed in separate workflows.
- Tax leakage is often reviewed after finance scenarios, not inside them.
- Investor Q&A and management narrative can become inconsistent across reporting cycles.
- Disclosure data quality is reviewed manually, limiting scalable AI adoption.

## Target Users

- **CFOs** who need board-ready views of refinancing risk, dividend sustainability, tax-adjusted cash flow, and capital-market pressure.
- **AMCs** that need asset-level risk rankings connected to occupancy, WALE, tenant concentration, capex need, valuation movement, and debt structure.
- **IR teams** that need consistent investor messaging, Q&A drafts, and disclosure-ready explanations grounded in structured evidence.
- **Risk management teams** that need early warning indicators for maturity walls, floating-rate exposure, asset concentration, disclosure gaps, and AI readiness controls.

## Solution Architecture

The MVP uses mock data in `/data`, reusable analytics in `/modules`, and six Streamlit pages in `/pages`.

```text
k-reit-cfo-copilot/
  app.py
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
    1_Client_Pain_Points.py
    2_Executive_Dashboard.py
    3_Scenario_Engine.py
    4_Asset_Debt_Risk.py
    5_AI_Memo_Investor_QA.py
    6_Data_Quality_AI_Readiness.py
```

## Tech Stack

- `streamlit` for the client-facing app.
- `pandas` for data loading and tabular transformation.
- `numpy` for scoring, clipping, and scenario math.
- `plotly` for executive charts and scenario visualizations.

## Six-Page Structure

1. **Client Pain Points**  
   Frames the customer problem before showing the solution: fragmented data, refinancing pressure, dividend credibility, tax leakage, repetitive investor Q&A, and disclosure quality gaps.

2. **Executive Dashboard**  
   Shows CFO-level signals including dividend coverage, refinancing risk, stressed LTV, AI readiness, debt maturity wall, asset watchlist, and open disclosure flags.

3. **Scenario Engine**  
   Provides sliders for interest rate shock, rent change, asset value change, and tax impact. Outputs include tax-adjusted cash flow, dividend coverage, refinancing risk, stressed LTV, dividend buffer, and peer comparison.

4. **Asset & Debt Risk**  
   Ranks assets by operating risk using occupancy, WALE, tenant concentration, and capex need. Connects asset risk to debt maturity concentration, floating-rate exposure, weighted coupon, LTV, and disclosure flags.

5. **AI Memo & Investor Q&A**  
   Generates rule-based CFO briefing memos and investor Q&A drafts from the scenario model, asset risk ranking, and disclosure flags. The MVP does not call external LLM APIs.

6. **Data Quality & AI Readiness**  
   Scores readiness across data availability, consistency, KPI standardization, scenario capability, tax-finance integration, and AI use case readiness. Produces a practical remediation roadmap for AX transformation.

## Mock REIT Coverage

The sample dataset includes three Korean listed REITs:

- SK REIT
- Lotte REIT
- ESR Kendall Square REIT

The data is illustrative and designed for prototype demonstration only.

## Business Impact

The prototype is intended to show how an AX consulting engagement can move from diagnosis to working decision support:

- Faster CFO attention allocation across refinancing, dividend, asset, and disclosure risks.
- More credible investor communication backed by structured evidence.
- Better integration of tax impact into cash-flow and capital allocation decisions.
- Repeatable scenario analysis for board, AMC, lender, and IR discussions.
- Clearer roadmap from current reporting data to AI-ready decision workflows.

## Future Roadmap

Planned enhancements:

- Replace mock CSVs with DART, market data, lender schedule, asset management, and IR data connectors.
- Add covenant headroom, swap/fixed-rate hedge modeling, and maturity refinancing assumptions.
- Expand tax logic for REIT-specific taxable income, withholding, property tax, and transaction tax scenarios.
- Add approval workflows for AI-generated memos and investor Q&A.
- Introduce retrieval-augmented generation over approved disclosures and IR materials.
- Build role-based views for CFO, AMC asset managers, IR officers, and external advisors.
- Add exportable board memo, lender pack, and investor FAQ outputs.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
