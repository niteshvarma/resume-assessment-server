from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from langchain_openai import ChatOpenAI
from .doc_parser import DocumentParser
from .resume_assessor_tool import ResumeAssessorTool
import os
import json

from .resume_assessor import ResumeAssessor

class ResumeAssessorRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Resume Assessor HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        self.assessor = ResumeAssessor(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            langchain_api_key = current_app.config['LANGCHAIN_API_KEY'],
            llm_model = current_app.config['LLM_MODEL'],
        )

        parsingInstruction = """The provided document is a resume for job application. Extract the following details from the resume:
        - Candidate's name
        - Candidate's location
        - Overall summary
        - Company
        - Role
        - Duration (start and end year)
        - Achievements and responsibilities as a list
        - Education and other credentials as a list
        """
        self.doc_parser = DocumentParser(current_app.config['LLAMA_CLOUD_API_KEY'])
        
        self.resume_parser = DocumentParser(
            current_app.config['LLAMA_CLOUD_API_KEY'],
            parsingInstruction)
        self.resume_assessor_tool = ResumeAssessorTool()
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))

 

    def post(self):        
        if 'job_description' not in request.files or 'resume' not in request.files:
            return jsonify({"error": "Both job_description and resume files are required"}), 400

        # Get uploaded files
        job_description_file = request.files['job_description']
        resume_file = request.files['resume']
        criteria_file = request.files['criteria']
        job_description = self.doc_parser.parse_document(job_description_file)
        resume = self.resume_parser.parse_document(resume_file)    
        criteria = self.doc_parser.parse_document(criteria_file)

        try:
            question = "Please assess the resume against the job description and criteria."
            assess_response = self.assessor.assess(job_description, criteria, resume, question)

            if assess_response.startswith("json"):
                assess_response = assess_response[4:].strip()
            
            logging.debug(f"Answer: {assess_response}")

            if not assess_response or not assess_response.strip():
                logging.error("Empty response received")
                return jsonify({"error": "Empty response from assessment tool"}), 500

            # If the response is a JSON string, parse it
            if isinstance(assess_response, str):
                parsed_response = json.loads(assess_response)

            # Return the parsed JSON as the HTTP response
            return jsonify({"AIResponse": parsed_response})
        except Exception as e:
            logging.error(f"Assessment failed: {e}")
            return "Server Error", 500
        

    def _test_data(self):
        job_desc = '''
        Vice President, Information Management and Technology.

        At SickKids Foundation, we believe relationships fuel meaningful change and inspire unparalleled philanthropic support. In this newly created strategic role, the Vice President of Information Management and Technology (IMT) will lead a team that shapes the future of digital innovation and technology and drive SickKids Foundation's digital transformation. The portfolio oversees digital services, enterprise platforms, data management, software development, infrastructure, and cybersecurity. Reporting to the Chief Information Officer (CIO), you will lead a team of passionate technology professionals to deliver transformative solutions that enable fundraising success and enhance donor experiences.
        
        Location: Toronto or Greater Toronto Area

        Required Skills:
        Strategic Leadership
        •	An active member of the senior leadership team and trusted partner to the CEO and fellow executives, playing a vital role in:
        o	Driving forward our mission, vision, and values with purpose and passion.
        o	Bringing our new strategic plan to life through innovative and impactful initiatives.
        o	Shaping both immediate and future goals that will define our success.
        •	Forge meaningful, collaborative relationships with both internal teams and external partners to maximize our shared impact.
        •	Champion a positive, forward-thinking culture that inspires excellence across our organization.
        •	Design and implement a secure, integrated ecosystem of digital services, data management, IT, and cloud infrastructure to power our next major fundraising campaign and beyond.
        •	Foster a culture of innovation, continuous learning, and leadership development within your team.

        Business Partnership & Innovation
        •	Lead the design and deployment of digital services that drive revenue growth, elevate donor experiences, and enhance operational efficiency.
        •	Partner with key departments to strategize and align digital initiatives with the unique objectives of our Fundraising, Marketing, and Operations teams.
        •	Drive innovation by envisioning and recommending next-generation solutions, including advanced data management strategies, cutting-edge business applications, and emerging technologies.
        •	Lead the establishment of a robust Data Governance framework. Work closely with stakeholders to ensure secure, compliant, and impactful data use, supported by best practices in systems and processes.
        •	Champion agile methodologies, fostering a culture of lean, iterative development to enhance lead times and quality across the organization.

        Enterprise Applications, Digital Services & Infrastructure Management
        •	Oversee the Foundation's Enterprise Applications including Constituent Relationship Management (Blackbaud CRM), Marketing Automation (Salesforce), Content Management System (Sitecore), Peer-to-Peer Fundraising & Event Management systems, e-Commerce (Shopify), Payment Processing (Stripe & Blackbaud) and Backoffice Operations.
        •	Oversee IT infrastructure, from cloud engineering (Microsoft Azure) and networking to workplace technology (Microsoft 365) and helpdesk support, ensuring reliable and innovative service delivery.
        •	Direct the IT Project Management Office (PMO) to align projects and investments with strategic business goals.
        •	Manage the Foundation's cybersecurity strategy, implementing advanced policies and technical safeguards to protect data and minimize risks.

        Team Leadership
        •	Develop, lead, attract, inspire, manage a diverse, talented, and high-performing team to ensure that the mission and core values of SickKids Foundation are put into practice by holding everyone accountable for supporting our goal of providing the Ultimate Donor Experience.
        •	Commitment to both personal and team professional development.
        •	Support the teams' efforts to achieve key performance indicators by providing strategic support, problem-solving, and the resources needed to succeed.

        Qualifications:
        While we know that for any job posting no one candidate will possess the qualifications being sought in equal measure, below is an outline of the qualifications we believe are important for a candidate to bring to the position or for the successful candidate to develop while in the role:

        •	10-15 years of experience in computer science or information technology related roles, including 5 years or more in senior leadership positions.
        •	Proven track record in building and managing strong data and technology teams.
        •	Experience in developing and implementing comprehensive strategies for digital services, applications, data management, software development, infrastructure, and security.
        •	Bachelor's degree in a relevant field such as computer science, or mathematics, is required.
        •	Master's degree, such as MBA in information technology or business management, would be considered an asset.
        •	Experience in program and project management processes (Metrics/KPIs) and methodologies, including Agile.
        •	Strong leadership, business relationship management, and team management skills.
        •	Experience in leading technology renewal and sustainable digital business transformations, including all aspects: people, process, and technology.
        •	Proficiency in leading application teams, full stack software development, enterprise architecture and infrastructure.
        '''
        
        criteria = '''
            1. Years and breadth of experience,
            2. Qualification as per job requirement with special focus on leadership experience,
            3. Education with an MBA or Master's degree strongly preferred
        '''

        resume = '''
        NITESH VARMA
        Toronto, Ontario, Canada |+1 416 200 5931 | varma.nitesh@gmail.com | linkedin.com/in/nvarma/

        PROFESSIONAL SUMMARY	
        Strategic technology leader with a proven ability to drive digital transformation, align IT strategies with business goals, and deliver secure, scalable digital ecosystems. Skilled in managing complex programs, fostering innovation, and leading cross-functional teams to deliver enterprise-grade solutions with measurable outcomes. Known for building strong executive partnerships, championing data governance and cybersecurity, and cultivating high-performance cultures.
        	Digital Transformation & Innovation: Modernized legacy platforms with cloud-native microservices, AI-driven automation, and scalable data access solutions, achieving $10M+ in annual savings and driving enhanced customer engagement.
        	Executive Collaboration: Aligned IT strategies with business goals through partnerships with C-suite leaders and guided the creation of a $30M, 4-year transformation roadmap, presented at the board level to secure strategic alignment and support.
        	Program Management: Oversaw portfolios with 8+ concurrent projects, including regulatory compliance, platform migrations, and transformation initiatives, ensuring seamless execution and alignment with strategic priorities.
        	Agile Leadership: Transitioned teams to Agile methodologies, reducing delivery lead times by 30% and improving solution quality.
        	Team Leadership: Directed global teams of 200+ professionals, fostering a high-performance culture and delivering large-scale IT initiatives.
        	Cybersecurity Leadership: Implemented portfolio-wide cybersecurity safeguards, enhancing compliance and mitigating risks across cloud and on-prem environments.

        WORK EXPERIENCE
        Technology Strategy Consultancy	Jan 2024 - Present
        Technology Strategy Consultant (Director) | RBCx Ventures, Toronto, ON	July 2024- Present

        Driving transformation roadmap and governance to RBCx companies' cloud-native application portfolio by advising on AWS account migration strategies, refining product roadmaps and alignment with enterprise architecture and cloud governance principles. Within a short period of 3 months, drove 4 application migration solutions through the RBC architecture governance process, providing the project green light to execute.

        Enterprise Architecture Consultant | WVE Digital, Toronto, ON (Remote)	Jan 2024- July 2024
        Short-term consulting engagements for European banks. Key Highlights:
        	Advised a major European on core banking modernization strategies, emphasizing scalability and resilience.
        	Conducted a strategic audit for a major Irish ban on SEPA Instant Credit Transfer (SCT Inst) implementation, ensuring regulatory alignment and readiness for a 2025 launch.

        Dayforce Inc. (Formerly Ceridian), Toronto, ON, Canada (Virtual/Remote-first)	Jan 2022 - Jul 2023
        Global Senior Director - Software Development | Team Size: 200+ | $50M P&L | $25M OpEx  
        Led the transformation of Dayforce's $400M+ payroll management business, driving end-to-end modernization of platform technology and processes to enable scalability, resilience, and operational excellence. Oversaw a global team across 10 development units, technology architecture unit, data & analytics division and production support functions spanning the U.S., Canada, Europe, and India.
        	Strategic Roadmap & Executive Alignment: Designed and executed a $30M, 4-year modernization roadmap for payroll platforms. Collaborated with executive stakeholders through regular interlock sessions to align technical initiatives with business priorities. Led the creation of the roadmap, which was presented at the board level, securing buy-in and ensuring strategic alignment to maximize impact.
        	Platform Modernization & Cloud Strategy: Directed a comprehensive Azure cloud migration, re-engineering payroll tax and payments systems using microservices, Kubernetes, and Kafka. Improved platform scalability by 10x and achieved $1M+ annual cost savings by transitioning from high-cost legacy systems to modern, cloud-based architectures, including Generative AI solutions for tax file transformation.
        	Complex Project Portfolio Management: Successfully managed a diverse portfolio of 8+ concurrent projects, encompassing transformation initiatives, multi-phase technology upgrades, data center migrations, product feature development, regulatory compliance, and legacy platform decommissioning. Directed overall technology vision, program management, resource planning, and executive reporting to ensure seamless execution and high-impact results.
        	Agile Transformation & Delivery Excellence: Implemented Agile methodologies, restructuring teams into product-aligned units that increased collaboration and delivery efficiency. Reduced project lead times by 20% and increased deployment frequency by 40% through enhanced DevOps practices, optimizing lead times and delivery quality.
        	Compliance & Cybersecurity Leadership: Achieved SOC2 certification, paving the way for National Trust Bank certification. Strengthened platform reliability and security by proactively addressing vulnerabilities and adhering to OWASP standards.
        	Team Leadership & Development: Cultivated a high-performance culture with an 88% employee engagement score and <5% attrition. Established robust career development pathways and partnered with HR to create a comprehensive career ladder, fostering talent retention and enabling team growth in a competitive market.

        Royal Bank of Canada (RBC), Toronto, ON, Canada	2010 - 2022
        Director, Development & Architecture | Financial Scope: $10M OpEx | Team Size: 35 	2019 - 2022
        Lead Architect, Commercial Credit | Team Size: 3	2015 - 2019
        Senior Manager, Solution Architecture	2010 - 2015

        Played a pivotal role in shaping technology strategy and engineering transformation over 12+ years at RBC, focusing on scalable, event-driven platforms and modernizing APIs to enhance data accessibility, customer experience, and operational efficiency. Honored with RBC Performance Awards in 2017 and 2019.
        	Strategic Technology Leadership: Defined long-term technology roadmaps aligned with RBC's business goals. Led high-impact modernization initiatives, enabling digital scalability and enhanced performance for client-facing and backend applications.
        	Core Platform Modernization: Re-architected RBC's core banking client data platform using event-driven architecture and API frameworks, supporting real-time data access and cross-functional integration. Delivered a Kafka-based Business Events platform that saved $10M+ annually and reduced mainframe costs by 20%.
        	Regulatory Compliance Expertise: As technical owner of the client data application portfolio for bank's 25m+ clients, directed compliance efforts for AML, FATCA, CRS, and other regulations, ensuring legal alignment and minimizing risk. Built robust frameworks and streamlined data pipelines to meet stringent reporting requirements and maintain operational integrity.
        	Governance & Collaboration: Streamlined architecture governance with a tiered model and Confluence/Jira-based frameworks, enhancing decision-making and communication across teams. Earned the 2017 RBC Performance Gold Award for this transformation.
        	Customer-Centric Digital Innovation: Delivered transformative client solutions, including RBC Express Mobile—Canada's first business banking app—and a USD-based auto financing solution that increased market share by 5%. Modernized platforms for cash management and insurance, driving adoption of self-service tools and enhancing advisor workflows.

        EARLY CAREER  

        Director (Senior Architect), Comcast Cable, London, ON, Canada	 2005 - 2010
        Various Software Development & Management Roles, Northern Virginia, USA	 1998 - 2005

        EDUCATION & PROFESSIONAL DEVELOPMENT 
        Executive MBA | Rotman School of Management, University of Toronto, Canada	2022
        Master of Science - Mechanical Engineering | Virginia Tech, Blacksburg, VA, USA	1998
        Bachelor of Science - Mechanical Engineering | National Institute of Technology, Jamshedpur, India	1995
        AWS Certified Solutions Architect	2024 
        Certificate in Generative AI, Large Language Model and Machine Learning | DeepLearning.ai/Coursera	2023 
        TOGAF 9.1 - Enterprise Architecture | The Open Group	2015
        '''