
# Risk stratification models for Population and Person Insights (PaPI)

## About PaPI

The PaPI (Population and Person Insights) project aims to review, improve, and update the risk stratification models used in PaPI dashboards. These dashboards provide critical insights into health and care services by analysing person-level linked data, including the National Bridges to Health Segmentation Dataset. The project specifically focuses on the "risk stratification" view - predicting the likelihood of:

- A&E attendance (Type 1 departments) within 12 months
- Emergency readmission within 12 months
- Emergency readmission within 30 days

The goal is to improve the accuracy and relevance of these risk predictions, which are currently based on pre-COVID data from 2019, by retraining the models and data pipelines following a platform migration (NCDR to UDAL). This will enable national, regional, and local health and care systems to better understand and manage population health risks.

![PaPI Dashboard](figure1.png)

## Why PaPI?

PaPI offers a modern, data-driven approach to understanding population health data, enabling national, regional, and local systems to:

- **Predict and prevent risks:** Identify high-risk individuals and cohorts to reduce avoidable admissions and improve outcomes.
- **Support evidence-based decisions:** Equip clinicians, senior leaders, and policymakers with insights tailored to their needs, ensuring informed and effective decisions.
- **Enhance resource efficiency:** Optimise financial and operational planning through accurate forecasting and stratification models.
- **Align with NHS priorities:** Drive preventive care initiatives, service recovery efforts, and trust-level benchmarking to meet national healthcare objectives.

This project puts patients at the centre to ensure they receive the best care and outcomes. By predicting the likelihood of a patient (or multiple patients) attending A&E, we can prepare adequately to provide care, thereby improving resource allocation. Our risk stratification approach aids in planning and prioritizing resources to meet patients’ needs, aligning with the NHS’s preventive care objectives.

## What we did – Risk stratification modelling

### Data

The data comes from two datasets, SUS and OBH Segmentation. This is pseudonymised person-level data, covering multiple sources (SUS, APC, outpatient, A&E, ECDS, community services, and mental health) from 2008 to 2023. The segmentation dataset splits the population into eight main groups (e.g., healthy, long-term conditions, serious disability, incurable cancer, organ failure, frailty/dementia, maternal and infant health, and acutely ill).

For the modelling, we use features like demographic details (age, gender, ethnicity), membership in the Bridges to Health (B2H) segment, over 50 medical conditions (e.g., Asthma, Atrial Fibrillation, COPD, Diabetes), and previous healthcare activity (e.g., number of A&E attendances).

### Methods

1. **Baseline Performance (Phase 1):**
   - Combine all segments with original features.
   - Test four ML models (Logistic Regression, SVM, Random Forest, XGBoost) with class balancing (1:1, 1:2).
   - No hyperparameter optimization.

2. **Segment-level Modelling (Phase 2):**
   - Model six population segments individually.
   - Use minimal feature sets and the same four algorithms.
   - Stratified cross-validation.

3. **Feature Refinement (Phase 3):**
   - Tailor features for poorly performing segments.
   - Remove irrelevant or low-importance features.
   - Use PCA for dimensionality reduction.

4. **Model Optimization (Phase 4):**
   - Fine-tune top-performing models.
   - Apply hyperparameter optimization.
   - Select best class balancing ratio (1:1 or 1:2).

5. **Interpretability & Explainability (Phase 5):**
   - Use SHAP values to explain feature importance.
   - Select best-performing models based on metrics and explainability.

## Key Exploitable Results (KERs) & Benefits

- **PaPI ways of working:** Showcases agile methods, ethics, and quality processes.
- **Code Carbon library integration:** Tracks CO₂ emissions during model training (publicly available on GitHub).
- **Risk stratification data asset:** Contributes to Population Health Management initiatives.

## Ethical Considerations & Compliance

We prioritise fairness and transparency, ensuring compliance with NHS policies.

## What’s Next?

The PaPI Project is currently in **Phase 4**, refining features and optimizing models. New features are added for poorly performing segments, while irrelevant features are removed based on segment overlap or low importance rankings (e.g., XGBoost feature importance ‘gains’). Data quality insights, such as highly correlated features, are also considered.

_Project summary last updated 12/02/2025 by Michelle Nwachukwu_
