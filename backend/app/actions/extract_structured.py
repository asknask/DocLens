"""
Extract structured data action - extracts entities and fields using LangChain.
"""
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.ir_models import DocumentIR


logger = logging.getLogger(__name__)


def get_llm() -> ChatOpenAI:
    """Get configured ChatOpenAI model."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def extract_structured_data(
    document_ir: DocumentIR,
    options: dict[str, Any] | None = None,
    output_format: str = "descriptive",
) -> dict[str, Any]:
    """
    Extract structured data from a document using LangChain.
    
    Args:
        document_ir: Extracted document content
        options: Optional configuration (schema, additional_fields)
        output_format: 'descriptive' for prose or 'json' for structured
        
    Returns:
        Extracted data with schema and confidence scores
    """
    options = options or {}
    
    # Get document text
    doc_text = document_ir.get_text_for_llm(max_chars=50000)
    
    if not doc_text.strip():
        if output_format == "json":
            return {
                "schema_used": {},
                "data": {},
                "confidence_by_field": {},
            }
        else:
            return {
                "description": "# Data Extraction Results\n\nNo data could be extracted as the document appears to be empty.",
            }
    
    # Determine schema to use
    custom_schema = options.get("schema")
    additional_fields = options.get("additional_fields", [])
    
    # Build the list of fields to extract
    if custom_schema:
        fields_to_extract = list(custom_schema.keys())
        schema_used = custom_schema
    else:
        fields_to_extract = ["entities", "dates", "amounts", "emails", "phones", "urls"]
        schema_used = {
            "entities": "list of strings",
            "dates": "list of strings",
            "amounts": "list of strings",
            "emails": "list of strings",
            "phones": "list of strings",
            "urls": "list of strings",
        }
    
    # Add additional fields if specified
    if additional_fields:
        for field in additional_fields:
            if field not in fields_to_extract:
                fields_to_extract.append(field)
                schema_used[field] = "string or list of strings"
    
    # Build field descriptions for prompt
    field_descriptions = []
    field_descriptions.append("- entities: Named entities (people, organizations, locations)")
    field_descriptions.append("- dates: Dates mentioned in the document")
    field_descriptions.append("- amounts: Monetary amounts or quantities")
    field_descriptions.append("- emails: Email addresses found")
    field_descriptions.append("- phones: Phone numbers found")
    field_descriptions.append("- urls: URLs or web addresses found")
    
    for field in additional_fields:
        field_descriptions.append(f"- {field}: Extract the {field} from the document")
    
    schema_description = "\n".join(field_descriptions)
    
    llm = get_llm()
    
    if output_format == "json":
        # Structured JSON output (original behavior)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction system. Your job is to extract specific information from documents accurately.

You MUST extract the following fields:
{schema_description}

IMPORTANT INSTRUCTIONS:
1. Extract ALL matching values for each field
2. Return values as lists when there are multiple matches
3. Return a single value (not in a list) if it's clearly a singular field like "date_of_birth"
4. If no data is found for a field, return an empty list [] or null
5. Be thorough - scan the entire document
6. For confidence scores, rate from 0.0 to 1.0 based on how certain you are about each extraction"""),
            ("user", """Please extract data from the following document:

---DOCUMENT START---
{document_text}
---DOCUMENT END---

Return a JSON object with exactly this structure:
{{
  "extracted_data": {{
    // Include each field with its extracted values
  }},
  "confidence": {{
    // Include confidence score (0.0-1.0) for each field
  }}
}}

Extract all the requested fields now."""),
        ])
        
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        chain = prompt | llm_with_json
        
        response = await chain.ainvoke({
            "document_text": doc_text,
            "schema_description": schema_description,
        })
        
        try:
            result = json.loads(response.content)
            extracted_data = result.get("extracted_data", result.get("data", {}))
            confidence = result.get("confidence", result.get("confidence_by_field", {}))
            
            if not extracted_data and not confidence:
                extracted_data = {k: v for k, v in result.items() if k not in ["confidence", "confidence_by_field"]}
                confidence = result.get("confidence", {})
            
            return {
                "schema_used": schema_used,
                "data": extracted_data,
                "confidence_by_field": confidence,
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return {
                "schema_used": schema_used,
                "data": {},
                "confidence_by_field": {},
                "error": "Failed to parse LLM response",
            }
    else:
        # Descriptive prose output
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction system. Extract and present information from the document in a clear, readable format.

Extract the following types of information:
{schema_description}

Write your response as a well-structured document with:
1. A summary of what was found
2. Each category of extracted data with clear headings
3. The values formatted in readable bullet points
4. Any notes about data quality or completeness

Use markdown formatting for headers, bullets, and emphasis."""),
            ("user", """Extract data from this document:

---
{document_text}
---"""),
        ])
        
        chain = prompt | llm
        
        result = await chain.ainvoke({
            "document_text": doc_text,
            "schema_description": schema_description,
        })
        
        return {"description": result.content}


def _schema_to_description(schema: dict[str, str]) -> str:
    """Convert a schema dict to prompt description."""
    lines = []
    for field, field_type in schema.items():
        lines.append(f"- {field}: {field_type}")
    return "\n".join(lines)
