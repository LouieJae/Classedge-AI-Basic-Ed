from .account_models import CustomUser, Profile, LoginHistory, get_upload_path, APIKey
from .legal_models import LegalDocument, UserLegalConsent

from .certificate_models import Certificate, certificate_upload_path
from .course_models import Course
from .display_image_models import DisplayImage, display_image_path
from .school_profile import SchoolName
from .student_sdg_models import StudentSDG
from .department_models import Department

__all__ = [
    # User models
    "CustomUser", "Profile", "LoginHistory", "get_upload_path",
    
    #Certificate models
    "Certificate", "certificate_upload_path",
    
    #Course models
    "Course",

    #Department models
    "Department",
    
    #Display Image models
    "DisplayImage", "display_image_path",
    
    #School Profile models
    "SchoolName",

    #Student SGD models
    "StudentSDG",

    #API Key models
    "APIKey",

    "UserLegalConsent",

    # Legal document
    "LegalDocument",

    ]
