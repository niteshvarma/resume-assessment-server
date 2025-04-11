from typing import Dict, Any
from .constants import ResumeMetadataKeys

class FilterNormalizer:
    # Maps LLM-extracted synonyms to canonical ResumeMetadataKeys
    KEY_SYNONYMS = {
        "role": ResumeMetadataKeys.LATEST_JOB_TITLE,
        "position": ResumeMetadataKeys.LATEST_JOB_TITLE,
        "location": ResumeMetadataKeys.LOCATION,
        "years_of_experience": ResumeMetadataKeys.YEARS_EXPERIENCE,
        "experience": ResumeMetadataKeys.YEARS_EXPERIENCE,
        "domain": ResumeMetadataKeys.CAREER_DOMAIN,
        "education": ResumeMetadataKeys.EDUCATION,
        "skills": ResumeMetadataKeys.TECHNICAL_SKILLS,
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
    def normalize(filters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize keys and values into proper format."""
        remapped = {}
        for raw_key, value in filters.items():
            key = FilterNormalizer.remap_key(raw_key)
            remapped[key] = value

        validated = FilterNormalizer.validate_keys(remapped)
        normalized = {}

        for k, v in validated.items():
            if k == ResumeMetadataKeys.YEARS_EXPERIENCE:
                if isinstance(v, int):
                    normalized[k] = FilterNormalizer.normalize_years_of_experience(v)
                elif isinstance(v, dict):
                    normalized[k] = v
            else:
                normalized[k] = v

        return normalized
