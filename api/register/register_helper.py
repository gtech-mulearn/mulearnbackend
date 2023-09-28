from db.user import User


def get_full_name(first_name, last_name):
    return f"{first_name}{last_name or ''}".replace(" ", "").lower()[:85]


def generate_mu_id(first_name, last_name):
    full_name = get_full_name(first_name, last_name)
    mu_id = f"{full_name}@mulearn"

    counter = 0
    while User.objects.filter(mu_id=mu_id).exists():
        counter += 1
        mu_id = f"{full_name}-{counter}@mulearn"

    return mu_id
