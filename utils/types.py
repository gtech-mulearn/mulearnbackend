from enum import Enum


class RoleType(Enum):
    EXPLORER = "Explorer"
    ADMIN = "Admins"
    DISCORD_MANAGER = "Discord Manager"
    DISTRICT_INTEREST_GROUP_LEAD = "District Interest Group Lead"
    EX_OFFICIAL = "Ex Official"
    FELLOW = "Fellow"
    ZONAL_CAMPUS_LEAD = "Zonal Campus Lead"
    STATE_CAMPUS_LEAD = "State Campus Lead"
    STATE_INTEREST_GROUP_LEAD = "State Interest Group Lead"
    APPRAISER = "Appraiser"
    DISTRICT_CAMPUS_LEAD = "District Campus Lead"
    MENTOR = "Mentor"
    INTERN = "Intern"
    CAMPUS_INTEREST_GROUP_LEAD = "Campus Interest Group Lead"
    ZONAL_INTEREST_GROUP_LEAD = "Zonal Interest Group Lead"
    CAMPUS_AMBASSADOR = "Campus Ambassador"
    BOT_DEV = "Bot Dev"
    PRE_MEMBER = "Pre Member"
    SUSPEND = "Suspended"
    STUDENT = "Student"
    MODERATOR = "Moderator"
    ENABLER = "Enabler"
    GTECH_ATFG = "Gtech ATFG"


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
    