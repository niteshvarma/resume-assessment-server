from enum import Enum

class ResumeMetadataKeys(str, Enum):
    # Basic identity
    CANDIDATE_NAME = "candidate_name"
    
    # Career-related
    JOB_TITLE = "job_title"
    CAREER_DOMAIN = "career_domain"
    YEARS_EXPERIENCE = "years_of_experience"
    CURRENT_LOCATION = "location"
    
    # Skills
    TECHNICAL_SKILLS = "technical_skills"
    LEADERSHIP_SKILLS = "leadership_skills"
    
    # Education
    EDUCATION = "highest_education_level"

    @classmethod
    def list_keys(cls):
        return [key.value for key in cls]
