import base64
import io
from werkzeug.datastructures import FileStorage
from flask import request, jsonify
import magic
from genfoundry.km.api.assess.assessor_runner import ResumeAssessorRunner

class Base64ResumeAssessHandler(ResumeAssessorRunner):
    ALLOWED_MIME_TYPES = {
        "application/pdf",  # PDF
        "application/msword",  # DOC
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # DOCX
    }

    def post(self):
        try:
            event = request.get_json()
            if "isBase64Encoded" in event:
                return self.handle_base64_request(event)
        except:
            pass  # Fall back to normal file handling

        return super().post()  # Call the parent class's post() method for normal requests

    def handle_base64_request(self, event):
        """Decodes Base64-encoded files and processes them."""
        try:
            job_description_file = self.decode_base64_file(event.get('body', {}).get('job_description', ""))
            resume_file = self.decode_base64_file(event.get('body', {}).get('resume', ""))
            criteria_file = self.decode_base64_file(event.get('body', {}).get('criteria', ""))
        except Exception as e:
            return jsonify({"error": f"Invalid Base64 file encoding: {str(e)}"}), 400

        return self.assess_resume(job_description_file, resume_file, criteria_file)

    def decode_base64_file(self, base64_string):
        """Converts Base64 string to a FileStorage object"""
        if not base64_string:
            raise ValueError("Empty file received")

        file_bytes = base64.b64decode(base64_string)
        file_stream = io.BytesIO(file_bytes)

                # Detect MIME type
        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(file_bytes)

        # Validate MIME type
        if file_mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid file type: {file_mime_type}. Only PDF, DOC, and DOCX are allowed.")

        return FileStorage(stream=file_stream)