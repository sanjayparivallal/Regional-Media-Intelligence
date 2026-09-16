"""Integration test verifying end-to-end media intelligence pipeline flow."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingestion.pdf_classifier import classify_pdf
from pipeline.nlp.language_detector import detect_language
from pipeline.nlp.translation.fallback_provider import FallbackTranslationProvider
from pipeline.nlp.entity.extractor import EntityExtractor
from pipeline.nlp.entity.brand_matcher import BrandMatcher
from pipeline.nlp.sentiment.lexicon import analyze_lexicon_sentiment
from pipeline.nlp.crisis.classifier import CrisisClassifier
from pipeline.nlp.crisis.risk_scorer import calculate_risk_score
from pipeline.alerting.generator import generate_alert


def test_full_pipeline_flow_mock():
    # 1. Ingestion / Classification
    pdf_class = classify_pdf("scanned_sample_page.jpg")
    assert pdf_class.document_type == "image"

    # 2. Regional Article Text (Hindi)
    headline_hi = "PayU पर RBI की सख्त कार्रवाई: नया प्रतिबंध लागू"
    body_hi = "भारतीय रिजर्व बैंक ने PayU पर नए मर्चेंट ऑनबोर्ड करने पर रोक लगा दी है। RBI ने कहा कि कंपनी ने नियमों का उल्लंघन किया है।"
    full_text_hi = f"{headline_hi}. {body_hi}"

    # 3. Language Detection
    lang_res = detect_language(full_text_hi)
    assert lang_res.language == "hi"
    assert lang_res.script == "devanagari"

    # 4. Entity Extraction & Protection
    extractor = EntityExtractor()
    entities = extractor.extract(full_text_hi, language="hi")
    protected_names = [e.text for e in entities if e.text in ["PayU", "RBI"]]

    # 5. Translation with Entity Protection
    translator = FallbackTranslationProvider()
    trans_res = translator.translate(
        text=full_text_hi,
        source_language="hi",
        target_language="en",
        protected_entities=protected_names or ["PayU", "RBI"],
    )
    assert "PayU" in trans_res.translated_text
    assert "RBI" in trans_res.translated_text

    # 6. Brand Matching
    brand_matcher = BrandMatcher()
    brand_matcher.load_brands([
        {
            "id": "payu-uuid-001",
            "name": "PayU",
            "aliases": ["PayU Finance", "PayU India"],
            "keywords": ["payment", "fintech"],
            "active": True,
        }
    ])
    matches = brand_matcher.match(trans_res.translated_text)
    assert len(matches) >= 1
    matched_brand = matches[0]
    assert matched_brand.brand_name == "PayU"

    # 7. Sentiment Analysis
    sentiment_res = analyze_lexicon_sentiment(
        f"penalty ban violation illegal action regulatory against PayU by RBI"
    )
    assert sentiment_res.label == "negative"

    # 8. Crisis Classification
    crisis_classifier = CrisisClassifier()
    crisis_res = crisis_classifier.classify(
        text="The RBI issued regulatory ban and fine on PayU for compliance failure",
        entities=["RBI", "PayU"],
        sentiment_label=sentiment_res.label,
        sentiment_confidence=sentiment_res.confidence,
    )
    assert crisis_res is not None
    assert crisis_res.topic in ("regulatory_action", "government_action")

    # 9. Explainable Risk Score
    risk = calculate_risk_score(
        sentiment_label=sentiment_res.label,
        sentiment_confidence=sentiment_res.confidence,
        brand_match_confidence=matched_brand.confidence,
        crisis_severity=crisis_res.severity,
        crisis_confidence=crisis_res.confidence,
        publication_reach=0.8,
        overall_ai_confidence=88.0,
    )
    assert risk.total >= 70.0
    assert risk.priority in ("critical", "high")

    # 10. Alert Generation & Deduplication
    alert = generate_alert(
        article_id="art-test-1",
        brand_id=matched_brand.brand_id,
        brand_name=matched_brand.brand_name,
        headline=headline_hi,
        crisis_topic=crisis_res.topic,
        risk_score=risk.total,
        risk_breakdown=risk.to_dict(),
        sentiment=sentiment_res.label,
        sentiment_confidence=sentiment_res.confidence,
        publication_name="Dainik Jagran",
        page_number=1,
        language="hi",
        region="North India",
    )
    assert alert.priority in ("critical", "high")
    assert alert.brand_id == "payu-uuid-001"
    assert len(alert.fingerprint) == 32
