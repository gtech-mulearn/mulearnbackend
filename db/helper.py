from decouple import config


def get_system_admin_id():
    from db.user import User
    return User.objects.get(pk=config("SYSTEM_ADMIN_ID"))
