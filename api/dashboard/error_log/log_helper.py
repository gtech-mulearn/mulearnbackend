import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from django.urls import Resolver404, URLPattern, URLResolver, get_resolver, resolve

from db.user import User
from utils.utils import DateTimeUtils


def check_url_match(url_to_check: str, pattern_to_match: str) -> bool:
    """
    Check if the given URL matches the specified pattern.

    Args:
        url_to_check (str): The URL to be checked.
        pattern_to_match (str): The pattern to match against.

    Returns:
        bool: True if the URL matches the pattern, False otherwise.
    """
    try:
        match = resolve(url_to_check)
        return match.url_name == pattern_to_match
    except Resolver404:
        return False


class ManageURLPatterns:
    def __init__(self):
        """
        Initialize a new instance of the FetchURLPatterns class.

        Args:
            self: The instance of the class itself.
        """
        self._url_patterns_cache = None
        self.urlpatterns = self._get_url_patterns()

    def _get_url_patterns(self):
        """
        Get the URL patterns by extracting them from the resolver.

        Returns:
            list: The list of extracted URL patterns.
        """
        if self._url_patterns_cache is not None:
            return self._url_patterns_cache
        self._url_patterns_cache = self._extract_url_patterns(
            get_resolver().url_patterns
        )
        return self._url_patterns_cache

    def _extract_url_patterns(self, url_patterns, prefix=""):
        """
        Recursively extract URL patterns including those nested within 'include()'.

        Args:
            url_patterns (list): The list of URL patterns to extract from.
            prefix (str): The prefix to prepend to the extracted patterns.

        Returns:
            list: The list of extracted URL patterns.
        """
        all_patterns = []
        for pattern in url_patterns:
            if isinstance(pattern, URLPattern):
                # This is a final URL pattern
                all_patterns.append(prefix + str(pattern.pattern))
            elif isinstance(pattern, URLResolver):
                # This is an 'include()' pattern, recurse into it
                nested_patterns = self._extract_url_patterns(
                    pattern.url_patterns, prefix + str(pattern.pattern)
                )
                all_patterns.extend(nested_patterns)
        return all_patterns

    @classmethod
    def group_patterns(cls, urlpatterns):
        """
        Group the URL patterns by their respective apps.

        Returns:
            dict: The dictionary of grouped URL patterns.
        """
        grouped_apis = defaultdict(lambda: defaultdict(list))
        for api in urlpatterns:
            # Split the API path and extract the primary and secondary category
            parts = api.split("/")
            if len(parts) > 3:
                primary_category = parts[2]  # e.g., 'register', 'dashboard'
                if primary_category in ["dashboard", "integrations"]:
                    # Subgroup for dashboard and integrations
                    secondary_category = parts[3]  # e.g., 'user', 'zonal'
                    grouped_apis[primary_category][secondary_category].append(api)
                else:
                    # Single group for other categories
                    grouped_apis[primary_category]["_general"].append(api)
        return grouped_apis


class logHandler:
    def __init__(self, log_data) -> None:
        self.log_data = log_data
        self.log_pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:"
            r".*?(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:|\Z)"
        )
        # Log entries their types and how to find them
        self.log_entries = {
            "id": {"regex": r"ID: (.+?)\n(?=TYPE:)", "type": str},
            "timestamp": {"regex": r"\n(.+?) ERROR.*", "type": datetime},
            "type": {"regex": r"TYPE: (.+?)\n(?=MESSAGE:)", "type": str},
            "message": {"regex": r"MESSAGE: (.+?)\n(?=METHOD:)", "type": str},
            "method": {"regex": r"METHOD: (.+?)\n(?=PATH:)", "type": str},
            "path": {"regex": r"PATH: (.+?)\n(?=AUTH:)", "type": str},
            "auth": {"regex": r"AUTH: \n(.+?)\n(?=BODY:)", "type": dict},
            "body": {"regex": r"BODY: \n(.+?)\n(?=TRACEBACK:)", "type": dict},
            "traceback": {"regex": r"TRACEBACK: (.+)$", "type": str},
        }

    def parse_logs(self, error_path) -> list[dict]:
        """parse a log value as str and convert it into
        appropriate types

        Returns:
            list[dict]: formatted errors
        """
        self.patch_pattern = (
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) ERROR PATCHED : (\w+)"
        )
        self.patched_errors = self.extract_patches(self.log_data)

        # Extract all logs in string format
        matches = reversed(re.findall(self.log_pattern, self.log_data, re.DOTALL))
        formatted_errors = {}
        for error in matches:
            # Separate each item in log
            log_entry = self.extract_log_entry(error)
            # combine them all to formatted_errors dict
            self.aggregate_log_entry(formatted_errors, log_entry)

        return formatted_errors.values()

    def extract_patches(self, log_data):
        return {
            patch[2]: self.get_formatted_time(patch[1])
            for patch in re.finditer(self.patch_pattern, log_data)
        }

    def extract_log_entry(self, error: str) -> dict:
        """fetch the value from the details of how to
        find it provided by the regex

        Args:
            error (str): the single matching error str

        Returns:
            dict: extracted log entry
        """
        values = self.get_values(error, *self.get_patterns())
        result_dict = {}

        for key, value in values.items():
            entry_type = self.log_entries[key]["type"]

            if entry_type == datetime:
                result_dict[key] = self.get_formatted_time(value)
            elif entry_type == dict and value:
                result_dict[key] = json.loads(value)
            else:
                result_dict[key] = value

        return result_dict

    def get_formatted_time(self, extracted_timestamp: str) -> datetime:
        """convert datetime from error log to readable datetime

        Args:
            extracted_timestamp (str): string datetime from error log

        Returns:
            datetime: converted datetime object
        """
        return datetime.strptime(
            extracted_timestamp.replace(",", "."), "%Y-%m-%d %H:%M:%S.%f"
        )

    def get_values(self, error: str, *patterns: str) -> dict:
        """fetches all values with the regex patterns

        Args:
            error (str): error string from log

        Returns:
            dict: fetched values
        """
        return {
            attr: self.extract_value(error, pattern)
            for attr, pattern in zip(self.log_entries.keys(), patterns)
        }

    def extract_value(self, error: str, pattern: str) -> str:
        """fetches a given value from the error with
        the provided regex

        Args:
            error (str): error string from log
            pattern (str): regex pattern

        Returns:
            str: fetched value
        """
        return value[1] if (value := re.search(pattern, error, re.DOTALL)) else None

    def get_patterns(self) -> list:
        """fetches all regex patterns

        Returns:
            list: regex patterns
        """
        values = self.log_entries.values()
        return [value["regex"] for value in values]

    def already_patched(self, log_entry: dict) -> bool:
        """checks if log entry id is in patched
        errors and its timestamp is before the error was patched
        """
        return (
            log_entry["id"] in self.patched_errors
            and log_entry["timestamp"] < self.patched_errors[log_entry["id"]]
        )

    def aggregate_log_entry(
        self, formatted_errors: list[dict], log_entry: dict
    ) -> None:
        """combines all fetched error into one

        Args:
            formatted_errors (list[dict]): the list to add everything into
            log_entry (dict):   current log entry
        """
        if not self.already_patched(log_entry):
            log_id = log_entry["id"]
            log_keys = self.log_entries.keys()
            if log_id not in formatted_errors:
                formatted_errors[log_id] = {
                    key: [] if key != "id" else log_id for key in log_keys
                }
            for key in log_keys:
                if (
                    key != "id"
                    and log_entry[key]
                    and log_entry[key] not in formatted_errors[log_id][key]
                ):
                    formatted_errors[log_id][key].append(log_entry[key])

    def get_urls_heatmap(self):
        """get the number of times each url is hit

        Args:
            urlpatterns (list): the list of url patterns

        Returns:
            dict: the number of times each url is hit
        """
        url_hits = {}

        for url_hit in re.finditer(self.log_entries["path"]["regex"], self.log_data):
            hit = url_hit.group(1)
            resolved = resolve(hit)
            matched_pattern = resolved.route

            if matched_pattern in url_hits:
                url_hits[matched_pattern] += 1
            else:
                url_hits[matched_pattern] = 1

        return url_hits

    def get_incident_info(self):
        """Get the time since the last incident in UTC.

        Returns:
            str: The time since the last incident in UTC.
        """
        last_incident = re.findall(
            self.log_entries["timestamp"]["regex"], self.log_data
        )[-1]

        last_incident_datetime = self.get_formatted_time(last_incident).replace(
            tzinfo=timezone.utc
        )
        current_datetime = DateTimeUtils.get_current_utc_time()

        time_since_then = current_datetime - last_incident_datetime

        return {
            "last_incident": last_incident_datetime,
            "time_since_then": time_since_then.total_seconds(),
        }

    def get_affected_users(self):
        """Get the number of affected users.

        Returns:
            int: The number of affected users.
        """
        affected_users = set(
            re.findall(r"\n *\"muid\" *: * \"(.+?@mulearn)\",", self.log_data)
        )

        return (len(affected_users) / User.objects.count()) * 100
