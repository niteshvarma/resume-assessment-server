from enum import Enum

class ResumeMetadataKeys(str, Enum):
    CANDIDATE_NAME = "candidate_name"
    LATEST_JOB_TITLE = "latest_job_title"
    CAREER_DOMAIN = "career_domain"
    YEARS_EXPERIENCE = "total_years_of_experience"
    TECHNICAL_SKILLS = "technical_skills"
    LEADERSHIP_SKILLS = "leadership_skills"
    EDUCATION = "highest_education_level"
    LOCATION = "current_location"

    @classmethod
    def list_keys(cls):
        return [key.value for key in cls]
