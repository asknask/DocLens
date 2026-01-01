"""
Tests for the instruction normalizer.
"""
import pytest
from app.models.api_models import ActionType
from app.actions.instruction_normalizer import (
    normalize_instructions,
    validate_action_options,
)


class TestNormalizeInstructions:
    """Tests for normalize_instructions function."""
    
    def test_brevity_short(self):
        """Test extraction of brevity=short."""
        result = normalize_instructions(
            "Keep it brief and concise",
            ActionType.SUMMARIZE,
            {}
        )
        assert result["options"]["brevity"] == "short"
    
    def test_brevity_detailed(self):
        """Test extraction of brevity=detailed."""
        result = normalize_instructions(
            "Give me a detailed and comprehensive summary",
            ActionType.SUMMARIZE,
            {}
        )
        assert result["options"]["brevity"] == "detailed"
    
    def test_language_extraction(self):
        """Test extraction of language preference."""
        result = normalize_instructions(
            "Respond in Spanish",
            ActionType.SUMMARIZE,
            {}
        )
        assert result["options"]["language"] == "Spanish"
    
    def test_bullet_format(self):
        """Test extraction of bullet format preference."""
        result = normalize_instructions(
            "Please use bullet points",
            ActionType.SUMMARIZE,
            {}
        )
        assert result["options"]["format"] == "bullets"
    
    def test_max_bullets(self):
        """Test extraction of bullet count for summarize."""
        result = normalize_instructions(
            "Give me 5 bullet points",
            ActionType.SUMMARIZE,
            {}
        )
        assert result["options"]["max_bullets"] == 5
    
    def test_focus_area(self):
        """Test extraction of focus area for summarize."""
        result = normalize_instructions(
            "Focus on the financial aspects",
            ActionType.SUMMARIZE,
            {}
        )
        assert "financial aspects" in result["options"]["focus"]
    
    def test_custom_labels_classify(self):
        """Test extraction of custom labels for classify."""
        result = normalize_instructions(
            "Categorize as legal, financial, or technical",
            ActionType.CLASSIFY,
            {}
        )
        assert "custom_labels" in result["options"]
        labels = result["options"]["custom_labels"]
        assert "legal" in labels
        assert "financial" in labels
        assert "technical" in labels
    
    def test_require_evidence_qa(self):
        """Test extraction of evidence requirement for QA."""
        result = normalize_instructions(
            "Please cite your sources",
            ActionType.QA,
            {}
        )
        assert result["options"]["require_evidence"] == True
    
    def test_target_format_transform(self):
        """Test extraction of target format for transform."""
        result = normalize_instructions(
            "Convert to JSON format",
            ActionType.TRANSFORM,
            {}
        )
        assert result["options"]["target_format"] == "json"
    
    def test_no_conflict_with_empty_options(self):
        """Test no error when options are empty."""
        result = normalize_instructions(
            "Make it brief",
            ActionType.SUMMARIZE,
            {}
        )
        assert "error" not in result
    
    def test_conflict_detection(self):
        """Test detection of conflicting format specifications."""
        result = normalize_instructions(
            "Use bullet points",
            ActionType.SUMMARIZE,
            {"format": "paragraphs"}
        )
        assert "error" in result
        assert "Conflicting format" in result["error"]
    
    def test_empty_refine(self):
        """Test handling of empty refine string."""
        result = normalize_instructions(
            "",
            ActionType.SUMMARIZE,
            {}
        )
        assert "options" in result
        assert result["options"] == {}


class TestValidateActionOptions:
    """Tests for validate_action_options function."""
    
    def test_qa_requires_question(self):
        """Test that QA action requires a question."""
        result = validate_action_options(ActionType.QA, {})
        assert result is not None
        assert result["error"] == "missing_required_option"
    
    def test_qa_valid_with_question(self):
        """Test that QA action is valid with a question."""
        result = validate_action_options(
            ActionType.QA,
            {"question": "What is the main topic?"}
        )
        assert result is None
    
    def test_summarize_no_requirements(self):
        """Test that summarize has no required options."""
        result = validate_action_options(ActionType.SUMMARIZE, {})
        assert result is None
    
    def test_classify_no_requirements(self):
        """Test that classify has no required options."""
        result = validate_action_options(ActionType.CLASSIFY, {})
        assert result is None
    
    def test_transform_no_requirements(self):
        """Test that transform has no strict requirements."""
        result = validate_action_options(ActionType.TRANSFORM, {})
        assert result is None
