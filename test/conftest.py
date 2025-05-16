# test/conftest.py
import sys
from unittest.mock import MagicMock

# Mock flask_jwt_extended early
sys.modules["flask_jwt_extended"] = MagicMock()

# Mock firebase_admin and submodules used
firebase_mock = MagicMock()
firebase_credentials_mock = MagicMock()
firebase_firestore_mock = MagicMock()
firebase_initialize_mock = MagicMock()

sys.modules["firebase_admin"] = firebase_mock
sys.modules["firebase_admin.credentials"] = firebase_credentials_mock
sys.modules["firebase_admin.firestore"] = firebase_firestore_mock
sys.modules["firebase_admin.initialize_app"] = firebase_initialize_mock
