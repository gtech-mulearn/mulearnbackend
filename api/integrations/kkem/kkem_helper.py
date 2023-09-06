import json
import requests


def send_data_to_kkem(kkem_link):
    response = requests.post(
        url="https://stagging.knowledgemission.kerala.gov.in/MuLearn/api/update/muLearnId",
        data=json.dumps(
            {
                "mu_id": kkem_link.user.mu_id,
                "jsid": int(kkem_link.integration_value),
                "email_id": kkem_link.user.email,
            }
        ),
        headers={"Authorization": f"Bearer {kkem_link.integration.token}"},
    )

    response_data = response.json()

    if not response_data["req_status"]:
        raise ValueError("Invalid jsid")

    return response.json()