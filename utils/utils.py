import datetime

import pytz


class DateTimeUtils:
    """
    A utility class for handling date and time operations.
    """

    @staticmethod
    def get_current_utc_time() -> datetime.datetime:
        """
        Returns the current time in UTC.

        Returns:
            datetime.datetime: The current time in UTC.
        """
        return DateTimeUtils.format_time(datetime.datetime.utcnow())

    @staticmethod
    def utc_to_local(utc_dt: datetime.datetime, local_tz: str) -> str:
        """
        Converts a UTC datetime object to a datetime object in the specified timezone.

        Args:
            utc_dt (datetime.datetime): The datetime object to convert.
            local_tz (str): The timezone to convert to.

        Returns:
            str: The converted datetime string in the format '%Y-%m-%d %I:%M:%S'.
        """
        utc_tz = pytz.timezone('UTC')
        local_tz = pytz.timezone(local_tz)
        utc_dt_naive = utc_dt.replace(tzinfo=None)
        utc_dt_utc = utc_tz.localize(utc_dt_naive)
        local_dt = utc_dt_utc.astimezone(local_tz)
        date_obj = datetime.datetime.fromisoformat(str(local_dt))
        formatted_date = date_obj.strftime("%Y-%m-%d %I:%M:%S")
        return formatted_date

    @staticmethod
    def format_time(date_time: datetime.datetime) -> datetime.datetime:
        """
        Formats a datetime object to the format '%Y-%m-%d %H:%M:%S'.

        Args:
            date_time (datetime.datetime): The datetime object to format.

        Returns:
            datetime.datetime: The formatted datetime object.
        """
        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
        return datetime.datetime.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def string_to_date_time(dt_str: str) -> datetime.datetime:
        """
        Converts a datetime string in the format '%Y-%m-%d %H:%M:%S' to a datetime object.

        Args:
            dt_str (str): The datetime string to convert.

        Returns:
            datetime.datetime: The converted datetime object.
        """
        return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


class _CustomHTTPHandler:
    @staticmethod
    def get_client_ip_address(request):
        req_headers = request.META
        x_forwarded_for_value = req_headers.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for_value:
            ip_addr = x_forwarded_for_value.split(",")[-1].strip()
        else:
            ip_addr = req_headers.get("REMOTE_ADDR")
        return ip_addr
