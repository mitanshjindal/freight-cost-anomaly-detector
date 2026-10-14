# FreightTiger Evaluation & Trustworthiness Report

## 1. Executive Summary
- **Total Labeled Test Cases**: 14
- **Cases Passing Gold Standard**: 14 / 14
- **Overall System Accuracy**: **100.0%**
- **Anomaly Detection F1 Score**: **100.0%** (Precision: 100.0%, Recall: 100.0%)
- **Evidence Justification F1 Score**: **100.0%** (Precision: 100.0%, Recall: 100.0%)

## 2. Quantitative Performance Metrics

### A. Anomaly Detection Classification
- **True Positives (TP)**: 7
- **False Positives (FP)**: 0
- **True Negatives (TN)**: 7
- **False Negatives (FN)**: 0
- **Precision**: 1.000
- **Recall**: 1.000
- **F1 Score**: 1.000

### B. Context Evidence Justification
- **True Positives (TP)**: 3
- **False Positives (FP)**: 0
- **True Negatives (TN)**: 11
- **False Negatives (FN)**: 0
- **Precision**: 1.000
- **Recall**: 1.000
- **F1 Score**: 1.000

## 3. Case-by-Case Benchmark Results

| Case ID | Route | Week | Expected Flag | Actual Flag | Expected Note | Actual Note | Verdict |
|---|---|---|---|---|---|---|---|
| `CASE_01` | Ahmedabad-Mumbai | 2025-01-20 | `No (justified)` | `No (justified)` | `N002` | `N002` | **[PASS]** |
| `CASE_02` | Chennai-Bangalore | 2025-02-24 | `No (justified)` | `No (justified)` | `N001` | `N001` | **[PASS]** |
| `CASE_03` | Chennai-Bangalore | 2025-03-03 | `No (justified)` | `No (justified)` | `N001` | `N001` | **[PASS]** |
| `CASE_04` | Chennai-Bangalore | 2025-03-10 | `Yes` | `Yes` | `` | `` | **[PASS]** |
| `CASE_05` | Delhi-Jaipur | 2024-11-11 | `Yes` | `Yes` | `` | `` | **[PASS]** |
| `CASE_06` | Delhi-Jaipur | 2024-11-18 | `Yes` | `Yes` | `` | `` | **[PASS]** |
| `CASE_07` | Mumbai-Pune | 2025-09-15 | `Yes` | `Yes` | `` | `` | **[PASS]** |
| `CASE_08` | Mumbai-Delhi | 2024-07-29 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_09` | Delhi-Jaipur | 2024-05-20 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_10` | Kolkata-Bhubaneswar | 2025-06-09 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_11` | Delhi-Chennai | 2024-01-01 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_12` | Mumbai-Pune | 2024-05-06 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_13` | Ahmedabad-Mumbai | 2024-08-12 | `No` | `No` | `` | `` | **[PASS]** |
| `CASE_14` | Kolkata-Bhubaneswar | 2025-01-13 | `No` | `No` | `` | `` | **[PASS]** |

## 4. Key Guardrail Verifications
1. **No Look-Ahead Leakage**: The rolling trailing baseline strictly evaluates weeks `< current_week_of`.
2. **Temporal Edge Disqualification**: Chennai-Bangalore on `2025-03-10` is an anomaly that occurred after flooding ended (March 8). The system correctly marks it as **unexplained** (`flagged=Yes`) and rejects N001/N009.
3. **Irrelevant Route Disqualification**: Note N004 mentions a toll plaza on a highway outside the dataset; it is never matched to any internal routes.
4. **Non-Justifying Semantics**: Notes describing stable demand (N006), road resurfacing (N007), normal conditions (N008), or cost-absorbed mandates (N010) are correctly rejected as justifications.

## 5. Evaluation Limitations & Scope
- **Benchmark Size**: The curated gold standard comprises 14 diverse route-weeks representing positive, negative, and edge cases. While this provides high signal for domain rules, real-world deployment requires continuous monitoring and human-in-the-loop audit sampling.
- **Single-Geography Assumption**: The current dataset represents Indian intercity corridors; applying to international multimodal freight would require extending the baseline logic to containerized sea/air routes.
