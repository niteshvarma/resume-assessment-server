from genfoundry.km.api.assess.assessor_runner_v2 import TextInputResumeAssessorRunner
#from genfoundry.km.api.assess.base64_assessor_runner import Base64ResumeAssessHandler
#from genfoundry.km.api.standardize.standardizer_runner import ResumeStandardizerRunner
from genfoundry.km.api.standardize.async_resume_processor_runner import AsyncResumeStandardizerRunner
from genfoundry.km.api.delete.delete_resume import ResumeDeleteRunner
from genfoundry.km.api.search.search_runner import ResumeQuery
from genfoundry.km.api.search.search_with_filters_runner import ResumeSearchWithFilterRunner
from genfoundry.km.api.extract_filters.extract_filters_runner import FilterExtractorRunner
from genfoundry.km.api.retrieve.retrieve_resume import ResumeRetrieverRunner
from genfoundry.km.api.pitchnotes.pitch_notes_generator_runner import PitchNotesGeneratorRunner
from genfoundry.km.api.candidateresearch.candidate_research_runner import CandidateResearchRunner
from genfoundry.km.api.admin.users.create_user import CreateUserRunner
from genfoundry.km.api.admin.users.login_jwt import LoginRunner
from genfoundry.km.api.admin.users.change_password import ChangePasswordRunner
from genfoundry.km.api.admin.tenants.create_tenant import CreateTenantRunner
from genfoundry.km.api.admin.tenants.list_tenants import ListTenantsRunner
from genfoundry.km.api.business_development.run_research import RunResearch
from genfoundry.km.api.analyze.analyzer_runner import ResumeAnalyzerRunner
from genfoundry.km.api.recruiting_insight.recruiting_insight_runner import RecruitingInsight

def register_routes(api):
    api.add_resource(TextInputResumeAssessorRunner, '/assess')
    #api.add_resource(ResumeAssessorAgentRunner, '/agent_assess')
    #api.add_resource(Base64ResumeAssessHandler, '/assess')
    api.add_resource(AsyncResumeStandardizerRunner, '/transform')
    api.add_resource(ResumeDeleteRunner, '/delete_resume')
    api.add_resource(ResumeQuery, '/search')
    api.add_resource(ResumeSearchWithFilterRunner, '/smart-search')
    api.add_resource(FilterExtractorRunner, '/extract-filters')
    api.add_resource(ResumeRetrieverRunner, '/resumedetails')
    api.add_resource(PitchNotesGeneratorRunner, '/pitchnotes')
    api.add_resource(CandidateResearchRunner, '/candidateresearch')
    api.add_resource(CreateUserRunner, '/create-user')
    api.add_resource(LoginRunner, '/login')
    api.add_resource(ChangePasswordRunner, '/change-password')
    api.add_resource(CreateTenantRunner, '/tenants/create')
    api.add_resource(ListTenantsRunner, '/tenants')
    api.add_resource(RunResearch, '/research/company')
    api.add_resource(ResumeAnalyzerRunner, '/analyze-resume')
    api.add_resource(RecruitingInsight, '/recruiting-insight')




    