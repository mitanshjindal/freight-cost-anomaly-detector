# FreightTiger Resource Usage & Operational Cost Report

## 1. Executive Summary
- **Execution Mode**: **Deterministic Operational Baseline (100% Offline / Zero Cloud Overhead)**
- **Engine / Architecture**: `Local Deterministic Engine & TF-IDF Index / Air-Gapped Python Rule Engine`
- **Total External Calls**: **0**
- **Total Input Tokens**: **0**
- **Total Output Tokens**: **0**
- **Total Operational Cost (USD)**: **$0.0000**
- **Total Operational Cost (INR)**: **₹0.00**

## 2. Resource Accounting Breakdown

| Metric | Recorded Value | Unit |
|---|---|---|
| Pipeline Architecture | Deterministic Operational Baseline (100% Offline / Zero Cloud Overhead) | — |
| Primary Engine | Local Deterministic Engine & TF-IDF Index | — |
| Component Configuration | Air-Gapped Python Rule Engine | — |
| External Calls Completed | 0 | calls |
| Input Tokens Processed | 0 | tokens |
| Output Tokens Synthesized | 0 | tokens |
| Published Input Rate | $0.000 | per 1M tokens |
| Published Output Rate | $0.000 | per 1M tokens |
| Exchange Rate Benchmark | ₹85.00 | per 1 USD |
| Operational Cost (USD) | **$0.0000** | USD |
| Operational Cost (INR) | **₹0.00** | INR |

## 3. Engineering Decisions & Architectural Guarantees
1. **Zero Mandatory Cost**: The baseline assessment executes without requiring paid external APIs, API keys, or cloud infrastructure.
2. **Selective Execution**: Routine non-anomalous route-weeks (711 out of 728 rows, or 97.7%) bypass external calls entirely and use deterministic templates.
3. **No Hallucination Risk**: Numerical verdicts and baseline percentages are computed deterministically in Python. The inference engine is never permitted to calculate or alter numerical flags.
4. **Audit Scope**: The production analysis run executed purely offline using deterministic rules and scikit-learn TF-IDF index. Zero external API calls were made and zero tokens were consumed. The pipeline is guaranteed 100% free of charge ($0.00) and completely air-gapped.
