# tests/test_extract_filters_tool.py
import sys
import os
from unittest.mock import MagicMock
import pytest
import json
from genfoundry.km.query.helper.filter_extractor import FilterExtractor
from genfoundry.km.query.helper.constants import ResumeMetadataKeys
from langchain_core.runnables.base import Runnable

# Mock flask_jwt_extended
sys.modules["flask_jwt_extended"] = MagicMock()

# Mocking `firebase_admin`
sys.modules["firebase_admin"] = MagicMock()

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class MockLLM(Runnable):
    def invoke(self, input, config=None, **kwargs):
        if isinstance(input, dict):
            question = input.get("question", "").lower()
        else:
            question = input.lower()

        if "software engineer" in question:
            return json.dumps({
                "filters": [
                    {"key": "latest_job_title", "value": "Software Engineer"}
                ]
            })

        elif "job trends" in question:
            # Simulate no filters found
            return json.dumps({
                "filters": []
            })

        elif "data scientist" in question and "new york" in question:
            return json.dumps({
                "filters": [
                    {"key": "latest_job_title", "value": "Data Scientist"},
                    {"key": "total_years_of_experience", "value": {"min": 3, "max": 7}},
                    {"key": "current_location", "value": "New York"}
                ]
            })

        else:
            return json.dumps({"filters": []})

    def batch(self, inputs, config=None, **kwargs):
        responses = []
        for item in inputs:
            if isinstance(item, dict) and "question" in item:
                input_text = item["question"]
            elif isinstance(item, str):
                input_text = item
            else:
                input_text = str(item)

            responses.append(self._mock_response(input_text))
        return responses

    def _mock_response(self, text):
        # Mock response for a Data Scientist with a location filter
        if "data scientist" in text.lower() and "new york" in text.lower():
            return json.dumps({
                "filters": [
                    {"key": "role", "value": "Data Scientist", "operator": "=="},
                    {"key": "years_of_experience", "value": {"min": 3, "max": 7}, "operator": "range"},
                    {"key": "location", "value": "New York", "operator": "=="},  # Add the location filter here
                ]
            })
        # Mock response for a Software Engineer without a location filter
        elif "software engineer" in text.lower():
            return json.dumps({
                "filters": [
                    {"key": "role", "value": "Software Engineer", "operator": "=="},
                ]
            })
        # Default mock response with empty filters
        return json.dumps({"filters": []})
    
class FaultyMockLLM(Runnable):
    def invoke(self, input, config=None, **kwargs):
        return "Not a JSON string"

            
def test_extract_filters_returns_expected_result():
    extractor = FilterExtractor(llm=MockLLM())
    question = "Find me a Data Scientist with 5 years of experience in New York"
    result = extractor.extract({"question": question})

    assert ResumeMetadataKeys.LATEST_JOB_TITLE in result
    assert result[ResumeMetadataKeys.LATEST_JOB_TITLE] == "Data Scientist"
    assert ResumeMetadataKeys.YEARS_EXPERIENCE in result
    assert result[ResumeMetadataKeys.YEARS_EXPERIENCE] == {"min": 3, "max": 7}


def test_extract_filters_returns_expected_result_with_location():
    extractor = FilterExtractor(llm=MockLLM())
    question = "Find me a Data Scientist with 5 years of experience in New York"
    result = extractor.extract({"question": question})
    
    # Log the result to understand the structure
    print("Result from invoke:", result)
    
    # Check if the necessary keys exist in the response
    assert ResumeMetadataKeys.LATEST_JOB_TITLE in result
    assert result[ResumeMetadataKeys.LATEST_JOB_TITLE] == "Data Scientist"
    
    assert ResumeMetadataKeys.YEARS_EXPERIENCE in result
    assert result[ResumeMetadataKeys.YEARS_EXPERIENCE] == {"min": 3, "max": 7}
    
    # Check for the location filter
    assert ResumeMetadataKeys.LOCATION in result
    assert result[ResumeMetadataKeys.LOCATION] == "New York"

def test_extract_filters_with_no_match():
    extractor = FilterExtractor(llm=MockLLM())
    question = "Tell me about job trends in tech"
    result = extractor.extract({"question": question})
    assert result == {}

def test_extract_filters_only_role():
    extractor = FilterExtractor(llm=MockLLM())
    question = "Find me a Software Engineer"
    result = extractor.extract({"question": question})
    assert ResumeMetadataKeys.LATEST_JOB_TITLE in result
    assert result[ResumeMetadataKeys.LATEST_JOB_TITLE] == "Software Engineer"

def test_extract_filters_case_insensitivity():
    extractor = FilterExtractor(llm=MockLLM())
    question = "FIND ME A data scientist"
    result = extractor.extract({"question": question})
    assert ResumeMetadataKeys.LATEST_JOB_TITLE in result

def test_extract_filters_invalid_json():
    extractor = FilterExtractor(llm=FaultyMockLLM())
    result = extractor.extract("Find me someone")
    assert result == {}  # Should fail gracefully
