# Pipeline Stage Execution Report

- **Target Image**: `7d4473f0-2884-49cf-bd9f-00b82d710969.jpeg`
- **Execution Timestamp**: `2026-09-20 20:18:10`
- **Overall Result**: **100% Passed**

## Pipeline Output Files in `backend/tests/output/`:

| Stage | Output File | Description |
| :--- | :--- | :--- |
| **Stage 1: Preprocessing** | `stage1_preprocessing.json`, `stage1_preprocessed.png` | Quality assessment & image normalization |
| **Stage 2: OCR** | `stage2_ocr_raw.txt`, `stage2_ocr_blocks.json`, `stage2_ocr_annotated.png` | EasyOCR text & bounding box extraction |
| **Stage 3: Segmentation** | `stage3_language_and_segmentation.json` | Language identification & news item parsing |
| **Stage 4: Translation** | `stage4_translation.json` | IndicTrans2 / English passthrough verification |
| **Stage 5: NER** | `stage5_ner_entities.json` | Extracted entities (SEBI, Adani, SEC, Reuters) |
| **Stage 6: Brand Matching** | `stage6_brand_mentions.json` | Monitored brand matches (Adani Enterprises, Ports, Group) |
| **Stage 7: Sentiment** | `stage7_sentiment_scores.json` | Multilingual XLM-RoBERTa negative classification |
| **Stage 8: Crisis Scoring** | `stage8_crisis_and_risk.json` | Crisis category and risk score evaluation |
| **Stage 9: Alerts** | `stage9_alerts.json` | 1 Actionable intelligence alerts generated |
