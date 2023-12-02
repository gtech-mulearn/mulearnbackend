import re
from datetime import datetime


class logHandler:
    def __init__(self) -> None:
        self.log_pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:"
            r".*?(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:|\Z)"
        )

        self.log_entries = {
            "id": r"ID: (.+?)\n(?=TYPE:)",
            "timestamp": r"^(.+?) ERROR.*",
            "type": r"TYPE: (.+?)\n(?=MESSAGE:)",
            "message": r"MESSAGE: (.+?)\n(?=METHOD:)",
            "method": r"METHOD: (.+?)\n(?=PATH:)",
            "path": r"PATH: (.+?)\n(?=AUTH:)",
            "auth": r"AUTH: \n(.+?)\n(?=BODY:)",
            "body": r"BODY: \n(.+?)\n(?=TRACEBACK:)",
            "traceback": r"TRACEBACK: (.+)$",
        }

    def parse_logs(self, log_data):
        matches = re.findall(self.log_pattern, log_data, re.DOTALL)
        formatted_errors = {}
        for error in matches:
            log_entry = self.extract_log_entry(error)
            self.aggregate_log_entry(formatted_errors, log_entry)

        return formatted_errors.values()

    def extract_log_entry(self, error):
        values = self.get_values(error, *self.get_patterns())
        return {
            key: self.get_formatted_time(value) if key == "timestamp" else value
            for key, value in values.items()
        }

    def get_formatted_time(self, extracted_timestamp):
        return datetime.strptime(
            extracted_timestamp.replace(",", "."), "%Y-%m-%d %H:%M:%S.%f"
        )

    def get_values(self, error, *patterns):
        return {
            attr: self.extract_value(error, pattern)
            for attr, pattern in zip(self.log_entries.keys(), patterns)
        }

    def extract_value(self, error, pattern):
        return value[1] if (value := re.search(pattern, error, re.DOTALL)) else None

    def get_patterns(self):
        return self.log_entries.values()

    def aggregate_log_entry(self, formatted_errors, log_entry):
        log_id = log_entry["id"]
        log_keys = self.log_entries.keys()
        if log_id not in formatted_errors:
            formatted_errors[log_id] = {
                key: set() if key != "id" else log_id for key in log_keys
            }
        for key in log_keys:
            if key != "id" and log_entry[key]:
                formatted_errors[log_id][key].add(log_entry[key])
