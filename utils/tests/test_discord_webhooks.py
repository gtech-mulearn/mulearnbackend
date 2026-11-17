"""
Unit tests for DiscordWebhooks: bulk role syncs are chunked under Discord's 2,000-character
message limit, and a rejected or failed post is reported instead of dropped. No database, no
network: requests.post, time.sleep and the webhook URL are patched.

    pytest --noconftest utils/tests/test_discord_webhooks.py
"""
import uuid
from unittest import mock

import pytest
import requests

from utils import utils as webhook_utils
from utils.utils import BULK_ROLE_CHUNK, DiscordWebhooks

URL = "https://discord.invalid/api/webhooks/1/token"
DISCORD_LIMIT = 2000


def _response(status, *, json_body=None, headers=None, text=""):
    resp = mock.Mock(status_code=status, headers=headers or {}, text=text)
    if json_body is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_body
    return resp


@pytest.fixture
def post(monkeypatch):
    monkeypatch.setattr(webhook_utils, "config", lambda key, default=None: URL if key == "DISCORD_WEBHOOK_LINK" else default)
    sleeps = []
    monkeypatch.setattr(webhook_utils.time, "sleep", sleeps.append)
    fake = mock.Mock(return_value=_response(204))
    monkeypatch.setattr(webhook_utils.requests, "post", fake)
    fake.sleeps = sleeps
    return fake


def _contents(post):
    return [c.kwargs["json"]["content"] for c in post.call_args_list]


def test_two_hundred_users_go_out_in_five_messages_under_the_limit(post):
    ids = [str(uuid.uuid4()) for _ in range(200)]

    assert DiscordWebhooks.bulk_role_updates("update", "Campus Lead", ids) is True

    contents = _contents(post)
    assert len(contents) == 200 // BULK_ROLE_CHUNK == 5
    assert all(len(c) <= DISCORD_LIMIT for c in contents)
    sent = [i for c in contents for i in c.split("<|=|>")[3].split(",")]
    assert sent == ids                                       # every id once, in order
    assert all(c.startswith("bulk-role<|=|>update<|=|>Campus Lead<|=|>") for c in contents)


def test_a_long_role_title_still_fits(post):
    ids = [str(uuid.uuid4()) for _ in range(BULK_ROLE_CHUNK)]
    DiscordWebhooks.bulk_role_updates("delete", "R" * 75, ids)   # role.title is at most 75 characters
    assert len(_contents(post)[0]) <= DISCORD_LIMIT


def test_empty_list_sends_nothing(post):
    assert DiscordWebhooks.bulk_role_updates("update", "Mentor", []) is True
    assert DiscordWebhooks.bulk_role_updates("update", "Mentor", [None, ""]) is True
    post.assert_not_called()


def test_one_rejected_chunk_makes_the_result_false_but_the_rest_are_sent(post):
    post.side_effect = [_response(204), _response(400, text="too long"), _response(204)]
    ids = [str(uuid.uuid4()) for _ in range(2 * BULK_ROLE_CHUNK + 1)]
    assert DiscordWebhooks.bulk_role_updates("update", "Mentor", ids) is False
    assert post.call_count == 3


@pytest.mark.parametrize("retry_kwargs, expected_sleep", [
    ({"json_body": {"retry_after": 0.75}}, 0.75),
    ({"headers": {"Retry-After": "2"}}, 2.0),
    ({}, 1.0),
    ({"json_body": {"retry_after": 30}}, 5.0),                 # capped: this runs on the request thread
], ids=["json", "header", "default", "capped"])
def test_rate_limit_is_retried_after_a_bounded_wait(post, retry_kwargs, expected_sleep):
    post.side_effect = [_response(429, **retry_kwargs), _response(204)]

    assert DiscordWebhooks.general_updates("role", "create", "Mentor") is True

    assert post.call_count == 2
    assert post.sleeps == [expected_sleep]


def test_rate_limit_gives_up_after_three_attempts(post, caplog):
    post.return_value = _response(429, json_body={"retry_after": 0.1}, text="slow down")
    assert DiscordWebhooks.general_updates("role", "create", "Mentor") is False
    assert post.call_count == 3 and len(post.sleeps) == 2
    assert any("rejected: HTTP 429" in r.getMessage() for r in caplog.records)


def test_rejected_post_is_logged_and_false(post, caplog):
    post.return_value = _response(400, text='{"content": ["Must be 2000 or fewer in length."]}')
    assert DiscordWebhooks.general_updates("bulk-role", "update", "Mentor", "a,b") is False
    (record,) = [r for r in caplog.records if r.levelname == "ERROR"]
    assert "HTTP 400" in record.getMessage() and "2000 or fewer" in record.getMessage()


def test_network_error_is_logged_and_false(post, caplog):
    post.side_effect = requests.exceptions.ConnectTimeout("timed out")
    assert DiscordWebhooks.general_updates("role", "create", "Mentor") is False
    (record,) = [r for r in caplog.records if r.levelname == "ERROR"]
    assert "failed to send" in record.getMessage() and record.exc_info


def test_no_webhook_configured_sends_nothing(post, monkeypatch):
    monkeypatch.setattr(webhook_utils, "config", lambda key, default=None: default)
    assert DiscordWebhooks.general_updates("role", "create", "Mentor") is False
    post.assert_not_called()


def test_post_uses_a_bounded_timeout(post):
    DiscordWebhooks.general_updates("role", "create", "Mentor")
    assert post.call_args.kwargs["timeout"] == (3, 5)
