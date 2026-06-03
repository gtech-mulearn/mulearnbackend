from enum import Enum


class ManagementType(Enum):
    CAMPUS = "Campus"
    HACKATHON = "Hackathon"
    USER_MANAGEMENT = "User Management"
    MANAGE_ORGANIZATION = "Manage Organization"
    TASK_MANAGEMENT = "Task Management"
    INTEREST_GROUP = "Interest Group"
    COLLEGE_LEVELS = "College Levels"
    KARMA_VOUCHER = "Karma Voucher"
    ERROR_LOG = "Error Log"
    DYNAMIC_TYPE = "Dynamic Type"
    MANAGE_ROLES = "Manage Roles"
    MANAGE_LOCATIONS = "Manage Locations"
    CHANNELS = "Channels"
    URL_SHORTENER = "Url Shortener"
    DISCORD_MODERATION = "Discord Moderation"

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
    TECH_TEAM = "Tech Team"
    IG_LEAD = "IG Lead"
    CAMPUS_ACTIVATION_TEAM = "Campus Activation Team"
    LEAD_ENABLER = "Lead Enabler"
    MULEARNER = "Mulearner"
    COMPANY = "Company"

    @classmethod
    def IG_CAMPUS_LEAD_ROLE(cls, ig_code: str):
        return f"{ig_code} CampusLead"

    @classmethod
    def IG_LEAD_ROLE(cls, ig_code: str):
        return f"{ig_code} IGLead"


class OrganizationType(Enum):
    COLLEGE = "College"
    COMPANY = "Company"
    COMMUNITY = "Community"
    SCHOOL = "School"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class WebHookActions(Enum):
    SEPARATOR = "<|=|>"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    UPDATE = "update"


class MainRoles(Enum):
    STUDENT = "Student"
    MENTOR = "Mentor"
    ENABLER = "Enabler"


class WebHookCategory(Enum):
    INTEREST_GROUP = "ig"
    COMMUNITY = "community"
    ROLE = "role"
    USER_ROLE = "user-role"
    USER = "user"
    USER_NAME = "user-name"
    USER_PROFILE = "user-profile"
    BULK_ROLE = "bulk-role"
    KARMA_INFO = "karma-info"


class RefferalType(Enum):
    KARMA = "Karma"
    MUCOIN = "Mucoin"


class IntegrationType(Enum):
    KKEM = "DWMS"


class TasksTypesHashtag(Enum):
    REFERRAL = "referral"
    MUCOIN = "mucoin"
    GITHUB = "social_github"
    FACEBOOK = "social_facebook"
    INSTAGRAM = "social_instagram"
    LINKEDIN = "social_linkedin"
    DRIBBLE = "social_dribble"
    BEHANCE = "social_behance"
    STACKOVERFLOW = "social_stackoverflow"
    MEDIUM = "social_medium"


class Events(Enum):
    LEARNING_FEST = "LearningFest"
    TOP_100_CODERS = "Top100"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class Lc(Enum):
    RECORD_SUBMIT_KARMA = 20
    RECORD_SUBMIT_HASHTAG = "#lcmeetreport"
    # Karma for creating a learning circle
    MEET_CREATE_KARMA = 1
    MEET_CREATE_HASHTAG = "#lc-meet-create"
    # Karma for joining a learning circle
    MEET_JOIN_KARMA = 1
    MEET_JOIN_HASHTAG = "#lc-meet-join"
    # Karma for submitting an attendee report
    ATTENDEE_REPORT_SUBMIT_KARMA = 2
    ATTENDEE_REPORT_SUBMIT_HASHTAG = "#lc-attendee-report"
    # Karma for submitting a learning circle report
    LC_REPORT_KARMA = 5
    LC_REPORT_HASHTAG = "#lc-meet-report"
    # karma when appraiser approved
    VERIFY_MAX_KARMA = 200
    VERIFY_HASHTAG = "#lc-meet-verify"


class CouponResponseKey(Enum):
    DISCOUNT_TYPE = "discount_type"
    DISCOUNT_VALUE = "discount_value"
    TICKET = "ticket"


class DiscountTypes(Enum):
    PERCENTAGE = "percentage"
    AMOUNT = "amount"


class LaunchPadLevels(Enum):
    LEVEL_1 = "IEEE Launchpad Level 1"
    LEVEL_2 = "IEEE Launchpad Level 2"
    LEVEL_3 = "IEEE Launchpad Level 3"
    LEVEL_4 = "IEEE Launchpad Level 4"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class LaunchPadRoles(Enum):
    ADMIN = "IEEEAdmin"
    DC = "IEEEDC"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class TFPTasksHashtags(Enum):
    SCRATCH = "#tfp2.0-scratch"
    COMMAND_LINE = "#tfp2.0-command-line"
    GIT_GITHUB = "#tfp2.0-git-github"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class LearningCircleRecurrenceType(Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


class UnitType(Enum):
    LEVEL = "level"
    KARMA = "karma"
    TASK = "task"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]


DEFAULT_HACKATHON_FORM_FIELDS = {
    "name": "system",
    "gender": "system",
    "email": "system",
    "mobile": "system",
    "college": "system",
    "experience": "input",
    "github": "input",
    "linkedin": "input",
    "bio": "input",
}


class SocialPlatformType(Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    DISCORD = "discord"
    GITHUB = "github"
    WEBSITE = "website"
    OTHER = "other"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]

class InternHashtag(Enum):
    DAILY_LOG_KARMA = 10
    DAILY_LOG_HASHTAG = "#intern-daily-log"
    WEEKLY_REVIEW_KARMA = 50
    WEEKLY_REVIEW_HASHTAG = "#intern-weekly-review"
    STREAK_7_KARMA = 20
    STREAK_7_HASHTAG = "#intern-streak-7"
    STREAK_14_KARMA = 50
    STREAK_14_HASHTAG = "#intern-streak-14"
    STREAK_30_KARMA = 100
    STREAK_30_HASHTAG = "#intern-streak-30"
    STREAK_60_KARMA = 200
    STREAK_60_HASHTAG = "#intern-streak-60"
    STREAK_90_KARMA = 500
    STREAK_90_HASHTAG = "#intern-streak-90"

class InternGuild(Enum):
    FRONTEND = "Frontend Guild"
    BACKEND = "Backend Guild"
    DESIGN = "Design Guild"
    MOBILE = "Mobile Guild"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]

class InternTaskCategory(Enum):
    BACKEND = ["Backend API", "Auth API", "Bot", "Database", "DevOps", "Documentation"]
    FRONTEND = ["UI Components", "API Integration", "Bug Fix", "Performance", "Accessibility", "Documentation"]
    DESIGN = ["Wireframes", "Prototyping", "Branding", "Research"]

class InternTaskStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    WAITING_FOR_REVIEW = "WAITING_FOR_REVIEW"

class InternTaskComplexity(Enum):
    LOW = ("LOW", 1)
    MEDIUM = ("MEDIUM", 2)
    HIGH = ("HIGH", 3)
    CRITICAL = ("CRITICAL", 5)

class InternSubmissionStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class InternLeaveType(Enum):
    SICK = ("SICK", 2)        # 2/month
    CASUAL = ("CASUAL", 1)    # 1/month
    EMERGENCY = ("EMERGENCY", 0)  # no cap
    WFH = ("WFH", 2)         # 2/week

class InternLeaveStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class InternGuildStatus(Enum):
    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"
    ON_LEAVE = "ON_LEAVE"
    INACTIVE = "INACTIVE"

class InternLeaderboardWeights:
    """Point-value multipliers for leaderboard scoring.
    Tunable without code changes - only this class needs updating."""
    KARMA_MULTIPLIER = 1           # karma value used directly
    DAILY_STREAK_MULTIPLIER = 50   # each streak day = 50 points
    WEEKLY_STREAK_MULTIPLIER = 200 # each streak week = 200 points
    COMPLETED_TASKS_MULTIPLIER = 30  # each completed task = 30 points
    COMPLEXITY_SCORE_MULTIPLIER = 20 # each complexity point = 20 points
