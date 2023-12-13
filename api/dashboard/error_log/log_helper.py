import json
import re
from datetime import datetime


class logHandler:
    def __init__(self) -> None:
        self.log_pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:"
            r".*?(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:|\Z)"
        )
        # Log entries their types and how to find them
        self.log_entries = {
            "id": {"regex": r"ID: (.+?)\n(?=TYPE:)", "type": str},
            "timestamp": {"regex": r"^(.+?) ERROR.*", "type": datetime},
            "type": {"regex": r"TYPE: (.+?)\n(?=MESSAGE:)", "type": str},
            "message": {"regex": r"MESSAGE: (.+?)\n(?=METHOD:)", "type": str},
            "method": {"regex": r"METHOD: (.+?)\n(?=PATH:)", "type": str},
            "path": {"regex": r"PATH: (.+?)\n(?=AUTH:)", "type": str},
            "auth": {"regex": r"AUTH: \n(.+?)\n(?=BODY:)", "type": dict},
            "body": {"regex": r"BODY: \n(.+?)\n(?=TRACEBACK:)", "type": dict},
            "traceback": {"regex": r"TRACEBACK: (.+)$", "type": str},
        }

    def parse_logs(self, log_data: str) -> list[dict]:
        """parse a log value as str and convert it into
        appropriate types

        Args:
            log_data (str): the single log data

        Returns:
            list[dict]: formatted errors
        """
        self.patch_pattern = (
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) ERROR PATCHED : (\w+)"
        )
        self.patched_errors = self.extract_patches(log_data)

        # Extract all logs in string format
        matches = reversed(re.findall(self.log_pattern, log_data, re.DOTALL))
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