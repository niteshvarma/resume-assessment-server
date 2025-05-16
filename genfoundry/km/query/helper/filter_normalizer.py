from typing import Dict, Any
from genfoundry.km.query.helper.constants import ResumeMetadataKeys
import logging
import json

logger = logging.getLogger(__name__)

class FilterNormalizer:
    # Maps LLM-extracted synonyms to canonical ResumeMetadataKeys
    KEY_SYNONYMS = {
        "role": ResumeMetadataKeys.JOB_TITLE,
        "position": ResumeMetadataKeys.JOB_TITLE,
        "job_title": ResumeMetadataKeys.JOB_TITLE,
        "location": ResumeMetadataKeys.CURRENT_LOCATION,
        "current_location": ResumeMetadataKeys.CURRENT_LOCATION,
        "years_of_experience": ResumeMetadataKeys.YEARS_EXPERIENCE,
        "experience": ResumeMetadataKeys.YEARS_EXPERIENCE,
        "domain": ResumeMetadataKeys.CAREER_DOMAIN,
        "career_domain": ResumeMetadataKeys.CAREER_DOMAIN,
        "education": ResumeMetadataKeys.EDUCATION,
        "highest_education_level": ResumeMetadataKeys.EDUCATION,
        "skills": ResumeMetadataKeys.TECHNICAL_SKILLS,
        "technical_skills": ResumeMetadataKeys.TECHNICAL_SKILLS,
        "tech_skills": ResumeMetadataKeys.TECHNICAL_SKILLS,
        "leadership": ResumeMetadataKeys.LEADERSHIP_SKILLS,
        "leadership_skills": ResumeMetadataKeys.LEADERSHIP_SKILLS,
        "candidate_name": ResumeMetadataKeys.CANDIDATE_NAME
    }

    @staticmethod
    def remap_key(key: str) -> str:
        """Map synonyms to canonical keys if known."""
        return FilterNormalizer.KEY_SYNONYMS.get(key, key)

    @staticmethod
    def validate_keys(filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and retain only keys matching ResumeMetadataKeys."""
        valid_keys = ResumeMetadataKeys.list_keys()
        return {k: v for k, v in filters.items() if k in valid_keys}

    @staticmethod
    def normalize_years_of_experience(years: int) -> Dict[str, int]:
        """Returns a range based on value."""
        buffer = 2 if years <= 5 else 3
        return {"min": max(0, years - buffer), "max": years + buffer}

    @staticmethod
    def normalize(raw_filters):
        """Normalize filters into a flat dict, supporting both list and dict formats."""
        logger.debug(f"Normalizing raw filters: {raw_filters}")

        normalized = {}

        if isinstance(raw_filters, dict):
            for key, val in raw_filters.items():
                try:
                    if isinstance(val, list):
                        parsed_list = []
                        for item in val:
                            try:
                                parsed_item = json.loads(item) if isinstance(item, str) else item
                            except (json.JSONDecodeError, TypeError):
                                parsed_item = item
                            parsed_list.append(parsed_item)
                        parsed_val = parsed_list
                    else:
                        parsed_val = json.loads(val) if isinstance(val, str) else val
                except (json.JSONDecodeError, TypeError):
                    parsed_val = val

                # Check if the value is a range [min, max], and convert it to GTE/LTE filters
                if isinstance(parsed_val, list) and len(parsed_val) == 2 and all(isinstance(v, (int, float)) for v in parsed_val):
                    normalized[key] = {"min": parsed_val[0], "max": parsed_val[1]}

                else:
                    normalized[key] = parsed_val

            logger.debug(f"Normalized filters from dict: {normalized}")
            return normalized

        elif isinstance(raw_filters, list):
            for filter_item in raw_filters:
                key = filter_item.get("name") or filter_item.get("key")
                value = filter_item.get("value")

                try:
                    parsed_value = json.loads(value) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value

                # Check if the value is a range [min, max], and convert it to GTE/LTE filters
                if isinstance(parsed_value, list) and len(parsed_value) == 2 and all(isinstance(v, (int, float)) for v in parsed_value):
                    normalized[key] = {"min": parsed_value[0], "max": parsed_value[1]}

                else:
                    normalized[key] = parsed_value

            logger.debug(f"Normalized filters from list: {normalized}")
            return normalized

        else:
            logger.error(f"Invalid filters format: {type(raw_filters)} – expected list or dict.")
            raise ValueError("Invalid filter format: expected a list or dict.")
