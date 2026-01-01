"""
Instruction normalizer - parses free-text refine instructions into structured options.
"""
import re
from typing import Any

from app.models.api_models import ActionType


def normalize_instructions(
    refine: str,
    action: ActionType,
    existing_options: dict[str, Any],
) -> dict[str, Any]:
    """
    Parse free-text refinement instructions into structured options.
    
    Args:
        refine: Free-text instructions from user
        action: The action being performed
        existing_options: Existing options from the request
        
    Returns:
        Dict with 'options' key containing extracted options,
        or 'error' key if instructions are unsupported/conflicting
    """
    refine_lower = refine.lower().strip()
    extracted = {}
    
    # Common patterns
    
    # Length/brevity preferences
    if any(word in refine_lower for word in ["brief", "short", "concise", "shorter"]):
        extracted["brevity"] = "short"
    elif any(word in refine_lower for word in ["detailed", "comprehensive", "thorough", "longer"]):
        extracted["brevity"] = "detailed"
    
    # Language preferences
    lang_patterns = [
        (r"in\s+(english|spanish|french|german|chinese|arabic|japanese|korean)", "language"),
        (r"translate\s+to\s+(\w+)", "language"),
        (r"respond\s+in\s+(\w+)", "language"),
    ]
    for pattern, key in lang_patterns:
        match = re.search(pattern, refine_lower)
        if match:
            extracted[key] = match.group(1).title()
    
    # Format preferences
    if "bullet" in refine_lower or "bullets" in refine_lower:
        extracted["format"] = "bullets"
    elif "paragraph" in refine_lower:
        extracted["format"] = "paragraphs"
    elif "json" in refine_lower:
        extracted["format"] = "json"
    elif "markdown" in refine_lower:
        extracted["format"] = "markdown"
    
    # Action-specific parsing
    
    if action == ActionType.SUMMARIZE:
        # Number of bullet points
        bullet_match = re.search(r"(\d+)\s*bullet", refine_lower)
        if bullet_match:
            extracted["max_bullets"] = int(bullet_match.group(1))
        
        # Focus areas
        focus_patterns = [
            (r"focus\s+on\s+(.+?)(?:\.|$)", "focus"),
            (r"emphasize\s+(.+?)(?:\.|$)", "focus"),
        ]
        for pattern, key in focus_patterns:
            match = re.search(pattern, refine_lower)
            if match:
                extracted[key] = match.group(1).strip()
    
    elif action == ActionType.EXTRACT_STRUCTURED:
        # Check for field requests
        fields_match = re.search(r"extract\s+(.+?)(?:\.|$|from)", refine_lower)
        if fields_match:
            fields_text = fields_match.group(1)
            # Split by common delimiters
            fields = re.split(r"[,\s]+and\s+|,\s*", fields_text)
            fields = [f.strip() for f in fields if f.strip()]
            if fields:
                extracted["additional_fields"] = fields
    
    elif action == ActionType.CLASSIFY:
        # Custom labels
        labels_match = re.search(r"categorize\s+as\s+(.+?)(?:\.|$)", refine_lower)
        if labels_match:
            labels_text = labels_match.group(1)
            labels = re.split(r"[,\s]+or\s+|,\s*", labels_text)
            labels = [l.strip() for l in labels if l.strip()]
            if labels:
                extracted["custom_labels"] = labels
    
    elif action == ActionType.QA:
        # Additional context
        if "with context" in refine_lower or "include context" in refine_lower:
            extracted["include_context"] = True
        
        # Evidence requirements
        if "with evidence" in refine_lower or "cite" in refine_lower or "quote" in refine_lower:
            extracted["require_evidence"] = True
    
    elif action == ActionType.TRANSFORM:
        # Target format
        format_patterns = [
            (r"convert\s+to\s+(\w+)", "target_format"),
            (r"transform\s+(?:in)?to\s+(\w+)", "target_format"),
            (r"as\s+(?:a\s+)?(\w+)", "target_format"),
        ]
        for pattern, key in format_patterns:
            match = re.search(pattern, refine_lower)
            if match:
                extracted[key] = match.group(1)
    
    # Check for conflicting instructions
    conflicts = _check_conflicts(extracted, existing_options, action)
    if conflicts:
        return {"error": conflicts}
    
    return {"options": extracted}


def _check_conflicts(
    extracted: dict[str, Any],
    existing: dict[str, Any],
    action: ActionType,
) -> str | None:
    """Check for conflicting instructions."""
    
    # Check for format conflicts
    if "format" in extracted and "format" in existing:
        if extracted["format"] != existing["format"]:
            return f"Conflicting format: options specify '{existing['format']}' but refine requests '{extracted['format']}'"
    
    # Action-specific conflict checks
    if action == ActionType.QA:
        if not existing.get("question") and "question" not in extracted:
            # QA without question in refine is not an error, question should be in options
            pass
    
    return None


def validate_action_options(
    action: ActionType,
    options: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Validate that options are valid for the given action.
    
    Returns:
        None if valid, or dict with error info if invalid
    """
    if action == ActionType.QA:
        if "question" not in options:
            return {
                "error": "missing_required_option",
                "message": "QA action requires 'question' option",
                "required": ["question"],
            }
    
    if action == ActionType.TRANSFORM:
        # Transform benefits from having a target format but it's not strictly required
        pass
    
    return None
