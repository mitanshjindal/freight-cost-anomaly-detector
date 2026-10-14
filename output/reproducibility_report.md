# FreightTiger Reproducibility Verification Report

## Executive Summary
- **Evaluation**: 3 independent runs on identical raw dataset (`data/shipment_records.csv`).
- **Byte-level Check**: **PASSED (100% Byte-Identical)**
- **DataFrame-level Check**: **PASSED (Identical DataFrames)**
- **Verdict & Numbers Stability**: 100% deterministic with zero variance across runs.

## Run Artifacts & Cryptographic Checksums

| Run | Output File | SHA-256 Hash | Row Count | Anomalies | Justified | Unexplained |
|---|---|---|---|---|---|---|
| Run 1 | `output/run_1.csv` | `7c640a3a9f93e01f402bbd23e8eaae035693f694be86c59f41032429b990a369` | 728 | 17 | 3 | 14 |
| Run 2 | `output/run_2.csv` | `7c640a3a9f93e01f402bbd23e8eaae035693f694be86c59f41032429b990a369` | 728 | 17 | 3 | 14 |
| Run 3 | `output/run_3.csv` | `7c640a3a9f93e01f402bbd23e8eaae035693f694be86c59f41032429b990a369` | 728 | 17 | 3 | 14 |

## Key Findings
1. **Zero Numerical Jitter**: Rolling 8-week trailing averages and peer averages yield identical values across all 728 route-week observations.
2. **Deterministic Ranking & Retrieval**: Context note retrieval and evidence validation produce invariant justification decisions.
3. **Deterministic CSV Serialisation**: RFC 4180 quoting and two-level sorting `(week_of ASC, route ASC)` guarantee byte-exact reproducibility.
