import csv
import datetime
from decouple import config
import requests
import pytz
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse


class CommonUtils:
    @staticmethod
    def get_paginated_queryset(queryset: QuerySet, request, fields) -> QuerySet:
        page = int(request.query_params.get("pageIndex", 1))
        per_page = int(request.query_params.get("perPage", 10))
        search_query = request.query_params.get('search')
        sort_by = request.query_params.get('sortBy')

        if search_query:
            query = Q()
            for field in fields:
                query |= Q(**{f'{field}__icontains': search_query})

            queryset = queryset.filter(query)

        if sort_by:
            queryset = queryset.order_by(sort_by)

        paginator = Paginator(queryset, per_page)
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = paginator.page(paginator.num_pages)

        return_data = {
            "queryset": queryset,
            "pagination": {
                "count": paginator.count,
                "totalPages": paginator.num_pages,
                "isNext": queryset.has_next(),
                "isPrev": queryset.has_previous(),
                "nextPage": queryset.next_page_number() if queryset.has_next() else None
            }
        }

        return return_data

    @staticmethod
    def generate_csv(queryset: QuerySet, csv_name: str) -> HttpResponse:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{csv_name}.csv"'
        fieldnames = list(queryset[0].keys())
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(queryset)

        return response


class DateTimeUtils:
    """
    A utility class for handling date and time operations.
    """

    @staticmethod
    def get_current_utc_time(timezone: str = "Asia/Kolkata") -> datetime.datetime:
        """
        Returns the current time in UTC.

        Returns:
            datetime.datetime: The current time in UTC.
        """
        utc_now = datetime.datetime.utcnow()
        local_tz = pytz.timezone(timezone)
        local_now = utc_now.replace(tzinfo=pytz.utc).astimezone(local_tz)
        return DateTimeUtils.format_time(local_now)

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

        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S %z")
        return datetime.datetime.strptime(formatted_time, "%Y-%m-%d %H:%M:%S %z")

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

class DiscordWebhooks:
    @staticmethod
    def discordWebhook(*args):
        content = f"{args[2]}<|=|>{args[1]}<|=|>{args[0]}"
        for arg in args[4:]:
            content = content + f"<|=|>{arg}"
        url = config(args[3])
        data = {
			# "username": f"{args[3]}",
			"content": content
		}
        requests.post(url, json=data)