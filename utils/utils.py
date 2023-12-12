import csv
import datetime
import gzip
import io
from datetime import timedelta

import decouple
import openpyxl
import pytz
import requests
from decouple import config
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.template.loader import render_to_string


class CommonUtils:
    @staticmethod
    def get_paginated_queryset(
        queryset: QuerySet,
        request,
        search_fields,
        sort_fields: dict = None,
        is_pagination: bool = True,
    ) -> QuerySet:
        if sort_fields is None:
            sort_fields = {}

        page = int(request.query_params.get("pageIndex", 1))
        per_page = int(request.query_params.get("perPage", 10))
        search_query = request.query_params.get("search")
        sort_by = request.query_params.get("sortBy")

        if search_query:
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": search_query})

            queryset = queryset.filter(query)

        if sort_by:
            sort = sort_by[1:] if sort_by.startswith("-") else sort_by
            if sort_field_name := sort_fields.get(sort):
                if sort_by.startswith("-"):
                    sort_field_name = f"-{sort_field_name}"

                queryset = queryset.order_by(sort_field_name)
        if is_pagination:
            paginator = Paginator(queryset, per_page)
            try:
                queryset = paginator.page(page)
            except PageNotAnInteger:
                queryset = paginator.page(1)
            except EmptyPage:
                queryset = paginator.page(paginator.num_pages)

            return {
                "queryset": queryset,
                "pagination": {
                    "count": paginator.count,
                    "totalPages": paginator.num_pages,
                    "isNext": queryset.has_next(),
                    "isPrev": queryset.has_previous(),
                    "nextPage": queryset.next_page_number()
                    if queryset.has_next()
                    else None,
                },
            }

        return queryset

    @staticmethod
    def generate_csv(queryset: QuerySet, csv_name: str) -> HttpResponse:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{csv_name}.csv"'
        fieldnames = list(queryset[0].keys())
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(queryset)

        compressed_response = HttpResponse(
            gzip.compress(response.content),
            content_type="text/csv",
        )
        compressed_response[
            "Content-Disposition"
        ] = f'attachment; filename="{csv_name}.csv"'
        compressed_response["Content-Encoding"] = "gzip"

        return compressed_response


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
        local_now = datetime.datetime.now(pytz.timezone("UTC"))
        return DateTimeUtils.format_time(local_now)

    @staticmethod
    def format_time(date_time: datetime.datetime) -> datetime.datetime:
        """
        Formats a datetime object to the format '%Y-%m-%d %H:%M:%S'.

        Args:
            date_time (datetime.datetime): The datetime object to format.

        Returns:
            datetime.datetime: The formatted datetime object.
        """

        return date_time.replace(microsecond=0)

    @staticmethod
    def get_start_and_end_of_previous_month():
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=start_date.month % 12 + 1
        ) - timedelta(days=1)
        return start_date, end_date


class _CustomHTTPHandler:
    @staticmethod
    def get_client_ip_address(request):
        req_headers = request.META
        return (
            x_forwarded_for_value.split(",")[-1].strip()
            if (x_forwarded_for_value := req_headers.get("HTTP_X_FORWARDED_FOR"))
            else req_headers.get("REMOTE_ADDR")
        )


class DiscordWebhooks:
    @staticmethod
    def general_updates(category, action, *values) -> str:
        """
        Modify channels and category in Discord
                Args:
        category(str): Category of webhook
        action(str): action of webhook
        values(str): values of webhook
        """
        content = f"{category}<|=|>{action}"
        for value in values:
            content = f"{content}<|=|>{value}"
        url = config("DISCORD_WEBHOOK_LINK")
        data = {"content": content}
        requests.post(url, json=data)


class ImportCSV:
    def read_excel_file(self, file_obj):
        workbook = openpyxl.load_workbook(filename=io.BytesIO(file_obj.read()))
        sheet = workbook.active

        rows = []
        for row in sheet.iter_rows(values_only=True):
            row_dict = {
                header.value: cell_value for header, cell_value in zip(sheet[1], row)
            }
            rows.append(row_dict)
        workbook.close()

        return rows


def send_template_mail(
    context: dict, subject: str, address: list[str], attachment: str = None
):
    """
    The function `send_user_mail` sends an email to a user with the provided user data, subject, and
    address.

    :param context: A dictionary containing user data such as name, email, and any other relevant
    information
    :param subject: The subject of the email that will be sent to the user
    :param address: The `address` parameter is a list of strings that represents the path to the email
    template file. It is used to specify the location of the email template file that will be rendered
    and used as the content of the email
    attachment: The Attachment That send to the user
    """

    from_mail = decouple.config("FROM_MAIL")

    base_url = decouple.config("FR_DOMAIN_NAME")
    status = None

    email_content = render_to_string(
        f"mails/{'/'.join(map(str, address))}", {"user": context, "base_url": base_url}
    )
    if not (mail := getattr(context, "email", None)):
        mail = context["email"]

    if attachment is None:
        status = send_mail(
            subject=subject,
            message=email_content,
            from_email=from_mail,
            recipient_list=[mail],
            html_message=email_content,
            fail_silently=False,
        )

    else:
        email = EmailMessage(
            subject=subject,
            body=email_content,
            from_email=from_mail,
            to=[context["email"]],
        )
        email.attach(attachment)
        email.content_subtype = "html"
        status = email.send()

    return status
