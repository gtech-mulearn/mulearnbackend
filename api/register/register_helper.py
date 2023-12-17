import decouple
import requests

from db.user import User
from utils.exception import CustomException
from utils.response import CustomResponse




def generate_muid(full_name):
    full_name = full_name.replace(" ", "").lower()[:85]
    muid = f"{full_name}@mulearn"

    counter = 0
    while User.objects.filter(muid=muid).exists():
        counter += 1
        muid = f"{full_name}-{counter}@mulearn"

    return muid


def get_auth_token(muid, password):
    AUTH_DOMAIN = decouple.config("AUTH_DOMAIN")
    response = requests.post(
        f"{AUTH_DOMAIN}/api/v1/auth/user-authentication/",
        data={"emailOrMuid": muid, "password": password},
    )
    response = response.json()
    if response.get("statusCode") != 200:
        raise CustomException(response.get("message"))

    return response.get("response")
