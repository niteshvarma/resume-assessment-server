from genfoundry.km.api.assess.assessor_runner import ResumeAssessorRunner
from genfoundry.km.api.assess.assessor_agent_runner import ResumeAssessorAgentRunner

def register_routes(api):
    api.add_resource(ResumeAssessorRunner, '/assess')
    api.add_resource(ResumeAssessorAgentRunner, '/agent_assess')

    