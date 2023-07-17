from enum import Enum


class RoleType(Enum):
    ADMIN = "Admins"
    DISCORD_MANAGER = "Discord Moderator"
    EX_OFFICIAL = "Ex Official"
    FELLOW = "Fellow"
    ASSOCIATE = "Associate"
    ZONAL_CAMPUS_LEAD = "Zonal Campus Lead"
    APPRAISER = "Appraiser"
    DISTRICT_CAMPUS_LEAD = "District Campus Lead"
    MENTOR = "Mentor"
    INTERN = "Intern"
    CAMPUS_LEAD = "Campus Lead"
    BOT_DEV = "Bot Dev"
    PRE_MEMBER = "Pre Member"
    SUSPEND = "Suspended"
    STUDENT = "Student"
    ENABLER = "Enabler"
    IG_FACILITATOR = "IG Facilitator"
    TECH_TEAM = 'Tech Team'


class OrganizationType(Enum):
    COLLEGE = 'College'
    COMPANY = 'Company'
    COMMUNITY = 'Community'


class WebHookActions(Enum):
    SEPERATOR = '<|=|>'
    CREATE = 'create'
    EDIT = 'edit'
    DELETE = 'delete'


class WebHookCategory(Enum):
    INTEREST_GROUP = 'ig'
    COMMUNITY = 'community'
    ROLE = 'role'


class TasksTypesHashtag(Enum):
    REFERRAL = '#refrral'


DEFAULT_HACKATHON_FORM_FIELDS = {
    'name': 'system',
    'gender': 'system',
    'email': 'system',
    'mobile': 'system',
    'bio': 'system',
    'college': 'system',
    'experience': 'input',
    'github': 'input',
    'linkedin': 'input',
}
