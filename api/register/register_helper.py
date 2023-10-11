from db.user import User


def get_full_name(first_name, last_name):
    return f"{first_name}{last_name or ''}".replace(" ", "").lower()[:85]


def generate_muid(first_name, last_name):
    full_name = get_full_name(first_name, last_name)
    muid = f"{full_name}@mulearn"

    counter = 0
    while User.objects.filter(muid=muid).exists():
        counter += 1
        muid = f"{full_name}-{counter}@mulearn"

    return muid
