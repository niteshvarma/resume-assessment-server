from genfoundry.km.api.assess.assessor_runner import ResumeAssessorRunner
from genfoundry.km.api.assess.assessor_agent_runner import ResumeAssessorAgentRunner
from genfoundry.km.api.standardize.standardizer_runner import ResumeStandardizerRunner
from genfoundry.km.api.delete.delete_resume import ResumeDeleteRunner
from genfoundry.km.api.chat.chat_runner import ResumeQuery

def register_routes(api):
    api.add_resource(ResumeAssessorRunner, '/assess')
    api.add_resource(ResumeAssessorAgentRunner, '/agent_assess')
    api.add_resource(ResumeStandardizerRunner, '/transform')
    api.add_resource(ResumeDeleteRunner, '/delete_resume')
    api.add_resource(ResumeQuery, '/chat')



    