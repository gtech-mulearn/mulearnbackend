import json
from base64 import urlsafe_b64decode
from urllib.parse import parse_qs

import requests
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad

from db.integrations import Integration
from utils.types import IntegrationType
from utils.utils import send_template_mail


def send_data_to_kkem(kkem_link):
    BASE_URL = kkem_link.integration.base_url

    response = requests.post(
        url=f"{BASE_URL}/MuLearn/api/update/muLearnId",
        data=json.dumps(
            {
                "muid": kkem_link.user.muid,
                "jsid": int(kkem_link.integration_value),
                "email_id": kkem_link.user.email,
            }
        ),
        headers={"Authorization": f"Bearer {kkem_link.integration.token}"},
    )

    response_data = response.json()

    if not response_data["request_status"]:
        raise ValueError("Invalid jsid")

    send_connection_successful_email(kkem_link.user)
    return response_data


def decrypt_kkem_data(ciphertext):
    try:
        secret_key = Integration.objects.get(name=IntegrationType.KKEM.value).auth_token

        SALT_SIZE = 16
        ITERATIONS = 10000
        KEY_SIZE = 256

        def ensure_padding(encoded_str):
            return encoded_str + "=" * (-len(encoded_str) % 4)

        salt_and_encrypted = urlsafe_b64decode(ensure_padding(ciphertext))
        salt = salt_and_encrypted[:SALT_SIZE]
        encrypted = salt_and_encrypted[SALT_SIZE:]

        secret = PBKDF2(
            secret_key,
            salt,
            dkLen=KEY_SIZE // 8,
            count=ITERATIONS,
            hmac_hash_module=SHA256,
        )

        cipher = AES.new(secret, AES.MODE_ECB)
        decrypted_data = cipher.decrypt(encrypted)
        try:
            decrypted = unpad(decrypted_data, AES.block_size)
        except:
            raise ValueError("Invalid padding or incorrect key")

        return parse_qs(decrypted.decode("utf-8"))
    except Exception as e:
        raise ValueError("The given token seems to be invalid do re-check and try again!")


def send_connection_successful_email(user):
    send_template_mail(
        context=user,
        subject="Integration Successfully Completed!",
        address=["KKEM", "integration_successful.html"],
    )
