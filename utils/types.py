from enum import Enum


class ManagementType(Enum):
    CAMPUS = 'Campus'
    COLLEGE = 'College'
    DISTRICT = 'District'
    DYNAMIC_MANAGEMENT = 'Dynamic Management'
    INTEREST_GROUP = 'Interest Group'
    KARMA_VOUCHER = 'Karma Voucher'
    LEARNING_CIRCLE = 'Learning Circle'
    LOCATION = 'Location'
    ORGANIZATION = 'Organization'
    PROFILE = 'Profile'
    REFERRAL = 'Referral'
    ROLE = 'Role'
    TASK = 'Task'
    USER = 'User'
    ZONAL = 'Zonal'
    HACKATHON = 'Hackathon'

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


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
    CAMPUS_ACTIVATION_TEAM = "Campus Activation Team"
    LEAD_ENABLER = "Lead Enabler"


class OrganizationType(Enum):
    COLLEGE = 'College'
    COMPANY = 'Company'
    COMMUNITY = 'Community'

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]

class WebHookActions(Enum):
    SEPARATOR = '<|=|>'
    CREATE = 'create'
    EDIT = 'edit'
    DELETE = 'delete'
    UPDATE = 'update'


class MainRoles(Enum):
    STUDENT = "Student"
    MENTOR = "Mentor"
    ENABLER = "Enabler"


class WebHookCategory(Enum):
    INTEREST_GROUP = 'ig'
    COMMUNITY = 'community'
    ROLE = 'role'
    USER_ROLE = 'user-role'
    USER = 'user'
    USER_NAME = 'user-name'
    USER_PROFILE = 'user-profile'


class RefferalType(Enum):
    KARMA = 'Karma'
    MUCOIN = 'Mucoin'


class IntegrationType(Enum):
    KKEM = 'DWMS'


class TasksTypesHashtag(Enum):
    REFERRAL = 'referral'
    MUCOIN = 'mucoin'
    GITHUB = 'social_github'
    FACEBOOK = 'social_facebook'
    INSTAGRAM = 'social_instagram'
    LINKEDIN = 'social_linkedin'
    DRIBBLE = 'social_dribble'
    BEHANCE = 'social_behance'
    STACKOVERFLOW = 'social_stackoverflow'
    MEDIUM = 'social_medium'


class Events(Enum):
    LEARNING_FEST = 'LearningFest'
    TOP_100_CODERS = 'Top100'

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class Lc(Enum):
    KARMA = 5
    TASK_HASHTAG = '#lcmeetreport'


DEFAULT_HACKATHON_FORM_FIELDS = {
    'name': 'system',
    'gender': 'system',
    'email': 'system',
    'mobile': 'system',
    'college': 'system',
    'experience': 'input',
    'github': 'input',
    'linkedin': 'input',
    'bio': 'input',
}
