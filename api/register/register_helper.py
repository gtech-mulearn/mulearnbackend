import decouple
import requests

from utils.exception import CustomException


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