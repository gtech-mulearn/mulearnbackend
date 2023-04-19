from enum import Enum

class RoleType(Enum):
    STUDENT = 'Student'
    MENTOR = 'Mentor'
    ENABLER = 'Enabler'

class OrganizationType(Enum):
    COLLEGE = 'College'
    COMPANY = 'Company'
    COMMUNITY = 'Community'