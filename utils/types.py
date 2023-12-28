from enum import Enum


class ManagementType(Enum):
    CAMPUS = 'Campus'
    HACKATHON = 'Hackathon'
    USER_MANAGEMENT = 'User Management'
    MANAGE_ORGANIZATION = 'Manage Organization'
    TASK_MANAGEMENT = 'Task Management'
    INTEREST_GROUP = 'Interest Group'
    COLLEGE_LEVELS = 'College Levels'
    KARMA_VOUCHER = 'Karma Voucher'
    ERROR_LOG = 'Error Log'
    DYNAMIC_TYPE = 'Dynamic Type'
    MANAGE_ROLES = 'Manage Roles'
    MANAGE_LOCATIONS = 'Manage Locations'
    CHANNELS = 'Channels'
    URL_SHORTENER = 'Url Shortener'
    DISCORD_MODERATION = 'Discord Moderation'

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
    TECH_TEAM = 'Tech Team'
    IG_LEAD = 'IG Lead'
    CAMPUS_ACTIVATION_TEAM = "Campus Activation Team"
    LEAD_ENABLER = "Lead Enabler"

    @classmethod
    def ig_campus_lead_role(cls,ig_code:str):
        return f"{ig_code} CampusLead"
    
    @classmethod
    def get_ig_lead_role(cls,ig_code:str):
        return f"{ig_code} IGLead"


class OrganizationType(Enum):
    COLLEGE = 'College'
    COMPANY = 'Company'
    COMMUNITY = 'Community'
    SCHOOL = 'School'

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
    BULK_ROLE = 'bulk-role'
    KARMA_INFO = 'karma-info'


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
    KARMA = 20
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
