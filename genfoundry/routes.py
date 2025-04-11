from genfoundry.km.api.assess.assessor_runner import ResumeAssessorRunner
#from genfoundry.km.api.assess.base64_assessor_runner import Base64ResumeAssessHandler
from genfoundry.km.api.assess.assessor_agent_runner import ResumeAssessorAgentRunner
from genfoundry.km.api.standardize.standardizer_runner import ResumeStandardizerRunner
from genfoundry.km.api.delete.delete_resume import ResumeDeleteRunner
from genfoundry.km.api.search.search_runner import ResumeQuery
from genfoundry.km.api.retrieve.retrieve_resume import ResumeRetrieverRunner
from genfoundry.km.api.pitchnotes.pitch_notes_generator_runner import PitchNotesGeneratorRunner
from genfoundry.km.api.candidateresearch.candidate_research_runner import CandidateResearchRunner
from genfoundry.km.api.admin.create_user import CreateUserRunner
from genfoundry.km.api.admin.login_jwt import LoginRunner
from genfoundry.km.api.admin.change_password import ChangePasswordRunner

def register_routes(api):
    api.add_resource(ResumeAssessorRunner, '/assess')
    #api.add_resource(ResumeAssessorAgentRunner, '/agent_assess')
    #api.add_resource(Base64ResumeAssessHandler, '/assess')
    api.add_resource(ResumeStandardizerRunner, '/transform')
    api.add_resource(ResumeDeleteRunner, '/delete_resume')
    api.add_resource(ResumeQuery, '/search')
    api.add_resource(ResumeRetrieverRunner, '/resumedetails')
    api.add_resource(PitchNotesGeneratorRunner, '/pitchnotes')
    api.add_resource(CandidateResearchRunner, '/candidateresearch')
    api.add_resource(CreateUserRunner, '/create-user')
    api.add_resource(LoginRunner, '/login')
    api.add_resource(ChangePasswordRunner, '/change-password')




    