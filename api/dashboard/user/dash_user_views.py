import uuid
from datetime import timedelta

import decouple
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Case, CharField, F, Q, Value, When
from django.utils.html import strip_tags
from rest_framework.views import APIView

from api.dashboard.user.dash_user_helper import mulearn_mails
from db.user import ForgotPassword, User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DateTimeUtils, DiscordWebhooks
from db.organization import UserOrganizationLink
from . import dash_user_serializer


class UserInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = User.objects.filter(mu_id=user_muid).first()

        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        response = dash_user_serializer.UserSerializer(user, many=False).data
        return CustomResponse(response=response).get_success_response()


class UserEditAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, user_id):
        # user = (
        #     User.objects.filter(id=user_id)
        #     .prefetch_related("user_organization_link_user_id")
        #     .first()
        # )
        # serializer = dash_user_serializer.UserEditSerializer(user)
        # return CustomResponse(response=serializer.data).get_success_response()
        user = User.objects.get(id=user_id)
        serializer = dash_user_serializer.UserEditDetailsSerializer(user).data
        return CustomResponse(response=serializer).get_success_response()


    @role_required([RoleType.ADMIN.value])
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.active = False
            user.save()
            return CustomResponse(
                general_message="User deleted successfully"
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = dash_user_serializer.UserEditSerializer(
                user, data=request.data, partial=True, context=request
            )

            if not serializer.is_valid():
                return CustomResponse(response=serializer.errors).get_failure_response()

            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()

        except Exception as e:
            return CustomResponse(response=str(e)).get_failure_response()


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, user_id=None):
        user_queryset = User.objects.annotate(
            total_karma=Case(
                When(total_karma_user__isnull=False, then=F("total_karma_user__karma")),
                default=Value(0),
            ),
            company=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COMPANY.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
            department=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__department__title"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            graduation_year=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__graduation_year"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            college=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COLLEGE.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
        )

        if user_id:
            user_data = user_queryset.filter(id=user_id)
            if not user_data:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response()
            serializer = dash_user_serializer.UserDashboardSerializer(
                user_data, many=True
            )
            return CustomResponse(response=serializer.data).get_success_response()
        else:
            queryset = CommonUtils.get_paginated_queryset(
                user_queryset,
                request,
                ["mu_id", "first_name", "last_name", "email", "mobile", "discord_id"],
                {
                    "first_name": "first_name",
                    "total_karma": "total_karma",
                    "email": "email",
                    "created_at": "created_at",
                },
            )
            serializer = dash_user_serializer.UserDashboardSerializer(
                queryset.get("queryset"), many=True
            )

            return CustomResponse().paginated_response(
                data=serializer.data, pagination=queryset.get("pagination")
            )


class UserManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = User.objects.annotate(
            total_karma=Case(
                When(total_karma_user__isnull=False, then=F("total_karma_user__karma")),
                default=Value(0),
            ),
            company=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COMPANY.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
            department=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__department__title"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            graduation_year=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__graduation_year"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            college=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COLLEGE.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
        )
        user_serializer_data = dash_user_serializer.UserDashboardSerializer(
            user_queryset, many=True
        ).data
        return CommonUtils.generate_csv(user_serializer_data, "User")


class UserVerificationAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = UserRoleLink.objects.filter(verified=False)
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["user__first_name", "user__last_name", "role__title"],
            {"fullname": "fullname"},
        )
        serializer = dash_user_serializer.UserVerificationSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, link_id):
        try:
            user = UserRoleLink.objects.get(id=link_id)
        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        user_serializer = dash_user_serializer.UserVerificationSerializer(
            user, data=request.data, partial=True
        )

        if not user_serializer.is_valid():
            return CustomResponse(
                response={"user_role_link": user_serializer.errors}
            ).get_failure_response()
        try:
            user_serializer.save()
            user_data = user_serializer.data

            DiscordWebhooks.channelsAndCategory(
                WebHookCategory.USER_ROLE.value,
                WebHookActions.UPDATE.value,
                user_data.user_id,
            )

            mulearn_mails().send_mail_mentor(user_data)

            return CustomResponse(
                response={"user_role_link": user_data}
            ).get_success_response()
        except IntegrityError as e:
            return CustomResponse(
                response={"user_role_link": str(e)}
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, link_id):
        try:
            link = UserRoleLink.objects.get(id=link_id)
            link.delete()
            return CustomResponse(
                general_message=["Link deleted successfully"]
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class ForgotPasswordAPI(APIView):
    def post(self, request):
        email_muid = request.data.get("emailOrMuid")

        if not (
            user := User.objects.filter(
                Q(mu_id=email_muid) | Q(email=email_muid)
            ).first()
        ):
            return CustomResponse(
                general_message="User not exist"
            ).get_failure_response()
        created_at = DateTimeUtils.get_current_utc_time()
        expiry = created_at + timedelta(seconds=900)  # 15 minutes
        forget_user = ForgotPassword.objects.create(  #
            id=uuid.uuid4(), user=user, expiry=expiry, created_at=created_at
        )
        email_host_user = decouple.config("EMAIL_HOST_USER")
        to = [user.email]

        domain = decouple.config("FR_DOMAIN_NAME")
        html_message = f"""
     <!DOCTYPE html>
<html lang="en">

<head>
    <meta name="__cloudhq_email_draft_json"
        content="eyJjb3VudGVycyI6eyJ1X3JvdyI6MTAsInVfY29sdW1uIjoxNiwidV9jb250ZW50X3RleHQiOjEwLCJ1X2NvbnRlbnRfaW1hZ2UiOjUsInVfY29udGVudF9idXR0b24iOjIsInVfY29udGVudF9zb2NpYWwiOjEsInVfY29udGVudF92aWRlbyI6MSwidV9jb250ZW50X2h0bWwiOjcsInVfY29udGVudF9oZWFkaW5nIjoxfSwiYm9keSI6eyJpZCI6InFVdVY1emFEWGciLCJyb3dzIjpbeyJpZCI6IjlmaVRZb2tmdzgiLCJjZWxscyI6WzEsMV0sImNvbHVtbnMiOlt7ImlkIjoiN1NKQUtYemZGRSIsImNvbnRlbnRzIjpbeyJpZCI6IlZsdmdJSFhoekgiLCJ0eXBlIjoiaW1hZ2UiLCJ2YWx1ZXMiOnsiY29udGFpbmVyUGFkZGluZyI6IjEwcHgiLCJhbmNob3IiOiIiLCJzcmMiOnsidXJsIjoiaHR0cHM6Ly9zaGFyZTEuY2xvdWRocS1ta3QzLm5ldC82NWUwYTcxZTMzYTVhNC5wbmciLCJ3aWR0aCI6MzUzLCJoZWlnaHQiOjI1MH0sInRleHRBbGlnbiI6ImNlbnRlciIsImFsdFRleHQiOiIiLCJhY3Rpb24iOnsibmFtZSI6IndlYiIsInZhbHVlcyI6eyJocmVmIjoiIiwidGFyZ2V0IjoiX2JsYW5rIn19LCJoaWRlRGVza3RvcCI6ZmFsc2UsImRpc3BsYXlDb25kaXRpb24iOm51bGwsIl9tZXRhIjp7Imh0bWxJRCI6InVfY29udGVudF9pbWFnZV8zIiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfaW1hZ2UifSwic2VsZWN0YWJsZSI6dHJ1ZSwiZHJhZ2dhYmxlIjp0cnVlLCJkdXBsaWNhdGFibGUiOnRydWUsImRlbGV0YWJsZSI6dHJ1ZSwiaGlkZWFibGUiOnRydWV9fV0sInZhbHVlcyI6eyJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbHVtbl80IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbHVtbiJ9LCJib3JkZXIiOnt9LCJwYWRkaW5nIjoiMHB4IiwiYmFja2dyb3VuZENvbG9yIjoiIn19LHsiaWQiOiJCZTE0RTdpRlBFIiwiY29udGVudHMiOlt7ImlkIjoiLU5YaEx0ZkpFXyIsInR5cGUiOiJpbWFnZSIsInZhbHVlcyI6eyJjb250YWluZXJQYWRkaW5nIjoiMTBweCIsImFuY2hvciI6IiIsInNyYyI6eyJ1cmwiOiJodHRwczovL3NoYXJlMS5jbG91ZGhxLW1rdDMubmV0LzBlNjhlNGY0YTI5NTM2LnBuZyIsIndpZHRoIjo0MjUsImhlaWdodCI6MjcwfSwidGV4dEFsaWduIjoiY2VudGVyIiwiYWx0VGV4dCI6IiIsImFjdGlvbiI6eyJuYW1lIjoid2ViIiwidmFsdWVzIjp7ImhyZWYiOiIiLCJ0YXJnZXQiOiJfYmxhbmsifX0sImhpZGVEZXNrdG9wIjpmYWxzZSwiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiX21ldGEiOnsiaHRtbElEIjoidV9jb250ZW50X2ltYWdlXzQiLCJodG1sQ2xhc3NOYW1lcyI6InVfY29udGVudF9pbWFnZSJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZSwiX292ZXJyaWRlIjp7Im1vYmlsZSI6eyJoaWRlTW9iaWxlIjp0cnVlfX19fV0sInZhbHVlcyI6eyJiYWNrZ3JvdW5kQ29sb3IiOiIiLCJwYWRkaW5nIjoiMHB4IiwiYm9yZGVyIjp7fSwiYm9yZGVyUmFkaXVzIjoiMHB4IiwiX21ldGEiOnsiaHRtbElEIjoidV9jb2x1bW5fOSIsImh0bWxDbGFzc05hbWVzIjoidV9jb2x1bW4ifX19XSwidmFsdWVzIjp7ImRpc3BsYXlDb25kaXRpb24iOm51bGwsImNvbHVtbnMiOmZhbHNlLCJiYWNrZ3JvdW5kQ29sb3IiOiIiLCJjb2x1bW5zQmFja2dyb3VuZENvbG9yIjoiI2ZmZmZmZiIsImJhY2tncm91bmRJbWFnZSI6eyJ1cmwiOiIiLCJmdWxsV2lkdGgiOnRydWUsInJlcGVhdCI6Im5vLXJlcGVhdCIsInNpemUiOiJjdXN0b20iLCJwb3NpdGlvbiI6InRvcC1jZW50ZXIiLCJjdXN0b21Qb3NpdGlvbiI6WyI1MCUiLCIwJSJdfSwicGFkZGluZyI6IjBweCIsImFuY2hvciI6IiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiX21ldGEiOnsiaHRtbElEIjoidV9yb3dfNCIsImh0bWxDbGFzc05hbWVzIjoidV9yb3cifSwic2VsZWN0YWJsZSI6dHJ1ZSwiZHJhZ2dhYmxlIjp0cnVlLCJkdXBsaWNhdGFibGUiOnRydWUsImRlbGV0YWJsZSI6dHJ1ZSwiaGlkZWFibGUiOnRydWUsImhpZGVNb2JpbGUiOmZhbHNlLCJub1N0YWNrTW9iaWxlIjpmYWxzZX19LHsiaWQiOiIwUllBOW9jeEtFIiwiY2VsbHMiOlszMy4zMywzMy4zNF0sImNvbHVtbnMiOlt7ImlkIjoidVNRbENMR3JQQiIsImNvbnRlbnRzIjpbeyJpZCI6Im9la1RYZ0FWUVMiLCJ0eXBlIjoiaHRtbCIsInZhbHVlcyI6eyJodG1sIjoiPGRpdiBzdHlsZT1cImRpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjogY29sdW1uO2FsaWduLWl0ZW1zOmNlbnRlclwiPlxuXG48ZGl2IGNsYXNzPVwiY29udGVudEhlYWRcIj5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPGgxIHN0eWxlPVwiIGZvbnQtc2l6ZTogMnJlbTtcbiAgICBtYXJnaW4tYm90dG9tOiAuNXJlbTt0ZXh0LWFsaWduOmNlbnRlcjt3aWR0aDozMHJlbTtcIj5SZXNldCBZb3VyIFBhc3N3b3JkPC9oMT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPHBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0eWxlPVwiZm9udC1zaXplOiAwLjhyZW07IGNvbG9yOiBncmF5OyBtYXJnaW46IDBweDt0ZXh0LWFsaWduOmNlbnRlcjtcIj5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFdlIHJlY2VpdmVkIGEgcmVxdWVzdCB0byByZXNldCB5b3VyXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwYXNzd29yZC4gPGJyPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgRG9uJ3Qgd29ycnksIHdlIGFyZSBoZXJlIHRvIGhlbHBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHlvdS5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9wPlxuICA8L2Rpdj48YnI+XG5cbiA8YSBocmVmPVwiaHR0cHM6Ly9tdWxlYXJuLm9yZy9cIj5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8YnV0dG9uIGhyZWY9XCJodHRwczovL211bGVhcm4ub3JnL1wiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY2xhc3M9XCJjb250ZW50UmVzZXRcIiBzdHlsZT1cIiBwYWRkaW5nOiAxcmVtO1xuICAgIGJvcmRlci1yYWRpdXM6IDI1cHg7XG4gICAgYm9yZGVyOiBub25lO1xuICAgIGNvbG9yOiAjZmZmO1xuICAgIGZvbnQtc2l6ZTogLjhyZW07d2lkdGg6MTVyZW07XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBiYWNrZ3JvdW5kLWltYWdlOiBsaW5lYXItZ3JhZGllbnQodG8gcmlnaHQsICMyRTg1RkUsICNBRjJFRTYpOyBcIj5SRVNFVCBNWSBQQVNTV09SRDwvYnV0dG9uPjwvYT48YnI+IDxwIGNsYXNzPVwiaWdub3JlXCJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc3R5bGU9XCJmb250LXNpemU6IDAuOHJlbTsgZm9udC13ZWlnaHQ6IDYwMDsgbWFyZ2luOiAwcHg7dGV4dC1hbGlnbjpjZW50ZXI7d2lkdGg6MThyZW07XCI+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIERpZG4ndCByZXF1ZXN0IGEgcGFzc3dvcmQgcmVzZXQ/IFlvdSBjYW5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc2FmZWx5IDxzcGFuPmlnbm9yZSB0aGlzIG1lc3NhZ2UuPC9zcGFuPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvcD5cbjwvZGl2PiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiY29udGFpbmVyUGFkZGluZyI6IjEwcHgiLCJhbmNob3IiOiIiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbnRlbnRfaHRtbF8zIiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfaHRtbCJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZX19XSwidmFsdWVzIjp7ImJhY2tncm91bmRDb2xvciI6IiIsInBhZGRpbmciOiIwcHgiLCJib3JkZXIiOnt9LCJib3JkZXJSYWRpdXMiOiIwcHgiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbHVtbl8xMCIsImh0bWxDbGFzc05hbWVzIjoidV9jb2x1bW4ifX19LHsiaWQiOiJ0M1VDQmtqZG9zIiwiY29udGVudHMiOlt7ImlkIjoickYwZGdrV25BMyIsInR5cGUiOiJpbWFnZSIsInZhbHVlcyI6eyJjb250YWluZXJQYWRkaW5nIjoiMHB4IiwiYW5jaG9yIjoiIiwic3JjIjp7InVybCI6Imh0dHBzOi8vc2hhcmUxLmNsb3VkaHEtbWt0My5uZXQvN2E4ZDYyZjQ4ZGQ5NDMucG5nIiwid2lkdGgiOjM0OCwiaGVpZ2h0Ijo0NDJ9LCJ0ZXh0QWxpZ24iOiJjZW50ZXIiLCJhbHRUZXh0IjoiIiwiYWN0aW9uIjp7Im5hbWUiOiJ3ZWIiLCJ2YWx1ZXMiOnsiaHJlZiI6IiIsInRhcmdldCI6Il9ibGFuayJ9fSwiaGlkZURlc2t0b3AiOmZhbHNlLCJkaXNwbGF5Q29uZGl0aW9uIjpudWxsLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbnRlbnRfaW1hZ2VfNSIsImh0bWxDbGFzc05hbWVzIjoidV9jb250ZW50X2ltYWdlIn0sInNlbGVjdGFibGUiOnRydWUsImRyYWdnYWJsZSI6dHJ1ZSwiZHVwbGljYXRhYmxlIjp0cnVlLCJkZWxldGFibGUiOnRydWUsImhpZGVhYmxlIjp0cnVlfX1dLCJ2YWx1ZXMiOnsiYmFja2dyb3VuZENvbG9yIjoiIiwicGFkZGluZyI6IjBweCIsImJvcmRlciI6e30sImJvcmRlclJhZGl1cyI6IjBweCIsIl9tZXRhIjp7Imh0bWxJRCI6InVfY29sdW1uXzExIiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbHVtbiJ9fX1dLCJ2YWx1ZXMiOnsiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiY29sdW1ucyI6ZmFsc2UsImJhY2tncm91bmRDb2xvciI6IiIsImNvbHVtbnNCYWNrZ3JvdW5kQ29sb3IiOiIiLCJiYWNrZ3JvdW5kSW1hZ2UiOnsidXJsIjoiIiwiZnVsbFdpZHRoIjp0cnVlLCJyZXBlYXQiOiJuby1yZXBlYXQiLCJzaXplIjoiY3VzdG9tIiwicG9zaXRpb24iOiJjZW50ZXIifSwicGFkZGluZyI6IjBweCIsImFuY2hvciI6IiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiX21ldGEiOnsiaHRtbElEIjoidV9yb3dfNyIsImh0bWxDbGFzc05hbWVzIjoidV9yb3cifSwic2VsZWN0YWJsZSI6dHJ1ZSwiZHJhZ2dhYmxlIjp0cnVlLCJkdXBsaWNhdGFibGUiOnRydWUsImRlbGV0YWJsZSI6dHJ1ZSwiaGlkZWFibGUiOnRydWV9fSx7ImlkIjoiQlI0Tl9Qa2pnMCIsImNlbGxzIjpbMSwxLDFdLCJjb2x1bW5zIjpbeyJpZCI6InBOVDlZeUtQbmMiLCJjb250ZW50cyI6W3siaWQiOiJkcmZneG9YQ2Z1IiwidHlwZSI6Imh0bWwiLCJ2YWx1ZXMiOnsiaHRtbCI6IjxkaXYgc3R5bGU9XCJ3aWR0aDoxMDBweFwiPjwvZGl2PiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiY29udGFpbmVyUGFkZGluZyI6IjEwcHgiLCJhbmNob3IiOiIiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbnRlbnRfaHRtbF82IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfaHRtbCJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZX19XSwidmFsdWVzIjp7ImJhY2tncm91bmRDb2xvciI6IiIsInBhZGRpbmciOiIwcHgiLCJib3JkZXIiOnt9LCJib3JkZXJSYWRpdXMiOiIwcHgiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbHVtbl8xMyIsImh0bWxDbGFzc05hbWVzIjoidV9jb2x1bW4ifX19LHsiaWQiOiJ2OGk1Sng5Ul84IiwiY29udGVudHMiOlt7ImlkIjoiYkQyWlRaNkFNaSIsInR5cGUiOiJodG1sIiwidmFsdWVzIjp7Imh0bWwiOiI8ZGl2IGNsYXNzPVwiY29udGVudEljb25zXCIgc3R5bGU9XCIgIGRpc3BsYXk6IGZsZXg7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuXG4gICAgZ2FwOiAzcmVtO1xuICAgIGZvbnQtc2l6ZTogMS41cmVtO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I6IGdyYXk7IFxuXCI+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxpbWcgc3R5bGU9XCJ3aWR0aDozMHB4XCJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyYz1cImh0dHBzOi8vaS5pYmIuY28vdmNkdjlwSi9saW5rZWRpbi5wbmdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYWx0PVwibGlua2VkaW5cIj5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPGltZyBzdHlsZT1cIndpZHRoOjMwcHhcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc3JjPVwiaHR0cHM6Ly9pLmliYi5jby9Gbk5OR3RQL2luc3RhLnBuZ1wiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBhbHQ9XCJpbnN0YVwiPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8aW1nIHN0eWxlPVwid2lkdGg6MzBweFwiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzcmM9XCJodHRwczovL2kuaWJiLmNvL3J5V1lTekIvdHdpdHRlci5wbmdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYWx0PVwidHdpdHRlclwiPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvZGl2PiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiY29udGFpbmVyUGFkZGluZyI6IjEwcHgiLCJhbmNob3IiOiIiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbnRlbnRfaHRtbF81IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfaHRtbCJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZSwiX292ZXJyaWRlIjp7Im1vYmlsZSI6eyJjb250YWluZXJQYWRkaW5nIjoiNnB4In19fX1dLCJ2YWx1ZXMiOnsiYmFja2dyb3VuZENvbG9yIjoiIiwicGFkZGluZyI6IjBweCIsImJvcmRlciI6e30sImJvcmRlclJhZGl1cyI6IjBweCIsIl9tZXRhIjp7Imh0bWxJRCI6InVfY29sdW1uXzE0IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbHVtbiJ9fX0seyJpZCI6ImxEMjJtanJNLV8iLCJjb250ZW50cyI6W3siaWQiOiJRNzREamRjanZ0IiwidHlwZSI6Imh0bWwiLCJ2YWx1ZXMiOnsiaHRtbCI6IjxkaXYgc3R5bGU9XCJ3aWR0aDoxMDBweFwiPjwvZGl2PiIsImhpZGVEZXNrdG9wIjpmYWxzZSwiZGlzcGxheUNvbmRpdGlvbiI6bnVsbCwiY29udGFpbmVyUGFkZGluZyI6IjEwcHgiLCJhbmNob3IiOiIiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbnRlbnRfaHRtbF83IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfaHRtbCJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZX19XSwidmFsdWVzIjp7ImJhY2tncm91bmRDb2xvciI6IiIsInBhZGRpbmciOiIwcHgiLCJib3JkZXIiOnt9LCJib3JkZXJSYWRpdXMiOiIwcHgiLCJfbWV0YSI6eyJodG1sSUQiOiJ1X2NvbHVtbl8xNSIsImh0bWxDbGFzc05hbWVzIjoidV9jb2x1bW4ifX19XSwidmFsdWVzIjp7ImRpc3BsYXlDb25kaXRpb24iOm51bGwsImNvbHVtbnMiOmZhbHNlLCJiYWNrZ3JvdW5kQ29sb3IiOiIiLCJjb2x1bW5zQmFja2dyb3VuZENvbG9yIjoiIiwiYmFja2dyb3VuZEltYWdlIjp7InVybCI6IiIsImZ1bGxXaWR0aCI6dHJ1ZSwicmVwZWF0Ijoibm8tcmVwZWF0Iiwic2l6ZSI6ImN1c3RvbSIsInBvc2l0aW9uIjoiY2VudGVyIn0sInBhZGRpbmciOiIwcHgiLCJhbmNob3IiOiIiLCJoaWRlRGVza3RvcCI6ZmFsc2UsIl9tZXRhIjp7Imh0bWxJRCI6InVfcm93XzEwIiwiaHRtbENsYXNzTmFtZXMiOiJ1X3JvdyJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZX19LHsiaWQiOiJMUEdLb05TMzdmIiwiY2VsbHMiOls1MF0sImNvbHVtbnMiOlt7ImlkIjoiaG83TUlCd243SyIsImNvbnRlbnRzIjpbeyJpZCI6InFmLTRuSHVidmciLCJ0eXBlIjoidGV4dCIsInZhbHVlcyI6eyJjb250YWluZXJQYWRkaW5nIjoiMTBweCIsImFuY2hvciI6IiIsImZvbnRTaXplIjoiMTRweCIsInRleHRBbGlnbiI6ImNlbnRlciIsImxpbmVIZWlnaHQiOiIxNDAlIiwibGlua1N0eWxlIjp7ImluaGVyaXQiOnRydWUsImxpbmtDb2xvciI6IiMwMDAwZWUiLCJsaW5rSG92ZXJDb2xvciI6IiMwMDAwZWUiLCJsaW5rVW5kZXJsaW5lIjp0cnVlLCJsaW5rSG92ZXJVbmRlcmxpbmUiOnRydWV9LCJoaWRlRGVza3RvcCI6ZmFsc2UsImRpc3BsYXlDb25kaXRpb24iOm51bGwsIl9tZXRhIjp7Imh0bWxJRCI6InVfY29udGVudF90ZXh0XzEwIiwiaHRtbENsYXNzTmFtZXMiOiJ1X2NvbnRlbnRfdGV4dCJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZSwidGV4dCI6IjxwIHN0eWxlPVwibGluZS1oZWlnaHQ6IDE0MCU7XCI+PHNwYW4gc3R5bGU9XCJjb2xvcjogIzAwMDAwMDsgdGV4dC1hbGlnbjogY2VudGVyOyB3aGl0ZS1zcGFjZTogbm9ybWFsOyBiYWNrZ3JvdW5kLWNvbG9yOiAjZjZmN2ZlOyBmbG9hdDogbm9uZTsgZGlzcGxheTogaW5saW5lOyBsaW5lLWhlaWdodDogMTkuNnB4O1wiPkdUZWNoIMK1TGVhcm4gfCBDb3B5cmlnaHQgwqkgMjAyMy4gQWxsIHJpZ2h0cyByZXNlcnZlZC48L3NwYW4+PC9wPiJ9fV0sInZhbHVlcyI6eyJiYWNrZ3JvdW5kQ29sb3IiOiIiLCJwYWRkaW5nIjoiMHB4IiwiYm9yZGVyIjp7fSwiYm9yZGVyUmFkaXVzIjoiMHB4IiwiX21ldGEiOnsiaHRtbElEIjoidV9jb2x1bW5fMTIiLCJodG1sQ2xhc3NOYW1lcyI6InVfY29sdW1uIn19fV0sInZhbHVlcyI6eyJkaXNwbGF5Q29uZGl0aW9uIjpudWxsLCJjb2x1bW5zIjpmYWxzZSwiYmFja2dyb3VuZENvbG9yIjoiIiwiY29sdW1uc0JhY2tncm91bmRDb2xvciI6IiIsImJhY2tncm91bmRJbWFnZSI6eyJ1cmwiOiIiLCJmdWxsV2lkdGgiOnRydWUsInJlcGVhdCI6Im5vLXJlcGVhdCIsInNpemUiOiJjdXN0b20iLCJwb3NpdGlvbiI6ImNlbnRlciJ9LCJwYWRkaW5nIjoiMHB4IiwiYW5jaG9yIjoiIiwiaGlkZURlc2t0b3AiOmZhbHNlLCJfbWV0YSI6eyJodG1sSUQiOiJ1X3Jvd185IiwiaHRtbENsYXNzTmFtZXMiOiJ1X3JvdyJ9LCJzZWxlY3RhYmxlIjp0cnVlLCJkcmFnZ2FibGUiOnRydWUsImR1cGxpY2F0YWJsZSI6dHJ1ZSwiZGVsZXRhYmxlIjp0cnVlLCJoaWRlYWJsZSI6dHJ1ZX19XSwidmFsdWVzIjp7InBvcHVwUG9zaXRpb24iOiJjZW50ZXIiLCJwb3B1cFdpZHRoIjoiNjAwcHgiLCJwb3B1cEhlaWdodCI6ImF1dG8iLCJib3JkZXJSYWRpdXMiOiIxMHB4IiwiY29udGVudEFsaWduIjoiY2VudGVyIiwiY29udGVudFZlcnRpY2FsQWxpZ24iOiJjZW50ZXIiLCJjb250ZW50V2lkdGgiOiI2MDBweCIsImZvbnRGYW1pbHkiOnsibGFiZWwiOiJDYWJpbiIsInZhbHVlIjoiJ0NhYmluJyxzYW5zLXNlcmlmIiwidXJsIjoiaHR0cHM6Ly9mb250cy5nb29nbGVhcGlzLmNvbS9jc3M/ZmFtaWx5PUNhYmluOjQwMCw3MDAiLCJkZWZhdWx0Rm9udCI6dHJ1ZX0sInRleHRDb2xvciI6IiMwMDAwMDAiLCJwb3B1cEJhY2tncm91bmRDb2xvciI6IiNGRkZGRkYiLCJwb3B1cEJhY2tncm91bmRJbWFnZSI6eyJ1cmwiOiIiLCJmdWxsV2lkdGgiOnRydWUsInJlcGVhdCI6Im5vLXJlcGVhdCIsInNpemUiOiJjb3ZlciIsInBvc2l0aW9uIjoiY2VudGVyIn0sInBvcHVwT3ZlcmxheV9iYWNrZ3JvdW5kQ29sb3IiOiJyZ2JhKDAsIDAsIDAsIDAuMSkiLCJwb3B1cENsb3NlQnV0dG9uX3Bvc2l0aW9uIjoidG9wLXJpZ2h0IiwicG9wdXBDbG9zZUJ1dHRvbl9iYWNrZ3JvdW5kQ29sb3IiOiIjREREREREIiwicG9wdXBDbG9zZUJ1dHRvbl9pY29uQ29sb3IiOiIjMDAwMDAwIiwicG9wdXBDbG9zZUJ1dHRvbl9ib3JkZXJSYWRpdXMiOiIwcHgiLCJwb3B1cENsb3NlQnV0dG9uX21hcmdpbiI6IjBweCIsInBvcHVwQ2xvc2VCdXR0b25fYWN0aW9uIjp7Im5hbWUiOiJjbG9zZV9wb3B1cCIsImF0dHJzIjp7Im9uQ2xpY2siOiJkb2N1bWVudC5xdWVyeVNlbGVjdG9yKCcudS1wb3B1cC1jb250YWluZXInKS5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOyJ9fSwiYmFja2dyb3VuZENvbG9yIjoiI2Y5ZjlmOSIsImJhY2tncm91bmRJbWFnZSI6eyJ1cmwiOiIiLCJmdWxsV2lkdGgiOnRydWUsInJlcGVhdCI6Im5vLXJlcGVhdCIsInNpemUiOiJjdXN0b20iLCJwb3NpdGlvbiI6InRvcC1jZW50ZXIiLCJjdXN0b21Qb3NpdGlvbiI6WyI1MCUiLCIwJSJdfSwicHJlaGVhZGVyVGV4dCI6IiIsImxpbmtTdHlsZSI6eyJib2R5Ijp0cnVlLCJsaW5rQ29sb3IiOiIjMDAwMGVlIiwibGlua0hvdmVyQ29sb3IiOiIjMDAwMGVlIiwibGlua1VuZGVybGluZSI6dHJ1ZSwibGlua0hvdmVyVW5kZXJsaW5lIjp0cnVlfSwiX21ldGEiOnsiaHRtbElEIjoidV9ib2R5IiwiaHRtbENsYXNzTmFtZXMiOiJ1X2JvZHkifX19LCJzY2hlbWFWZXJzaW9uIjoxNX0=">

    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="x-apple-disable-message-reformatting">

    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title></title>
</head>

<body style="width: 100%;height: 100%;">
    <center>

        <div style=" width: 400px; height: 800px;">
            <center>

                <img style="width: 400px;height: 220px;" src="https://iili.io/HQFW5rB.png" alt="HLi9NHP.md.png"
                    border="0">

                <div style="background: transparent;width: 100%;height: 170px;">
                    <center>
                        <h1 style="color: black;font-family: 'Poppins';font-weight: 600;font-size: 30px;">REFRESH YOUR
                            SECRETS</h1>
                        <P style="color: rgb(65, 64, 64);font-family: 'Poppins';line-height: 1.2;font-size: 13px;">Hey
                            there, we got a request to fix up your password!
                            Don't worry, click the button below to reset your password!
                        </P>
                        <div style="width: 100%;height: 10px;background: transparent;"></div>

                    
                        <a href="{domain}/reset-password?token={forget_user.id}/" style="width:160px;height: 40px;"> 
                            <img style="width:160px;height: 40px;" src="https://iili.io/HQFXsFp.png" alt=""></a>
                        <div style="width: 100%;height: 10px;background: transparent;"></div>
                        <p style="color: black;font-family: 'Poppins';line-height: 1.2;font-size: 13px;">Didn't request
                            a password reset? You can ignore this email then.</p>
                    </center>
                </div>
                <div style="background: transparent;width: 100%;height: 100px;"></div>
                <div style="background: transparent;width: 100%;height: 160px;">
                    <center>
                        <a href="https://mulearn.org/" style="width: 120px;height: 30px;"><img
                                style="width: 120px;height: 30px;" src="https://i.ibb.co/zZCJkgg/Learn.png" alt="Learn"
                                border="0"></a>
                        <div style="background:transparent ;width: 370px;height: 10px;"></div>

                        <div style="background:rgba(0, 0, 0, 0.37) ;width: 370px;height: 2px;"></div>
                        <div style="background:transparent ;width: 370px;height: 10px;"></div>
                        <div style="background:transparent ;width: 100px;display: flex;">

                            <a style="width: 20px;height: 20px;" href="https://www.linkedin.com/company/mulearn/"><img
                                    style="width: 15px;height: 15px;" src="https://i.ibb.co/RYr8YHc/linkedin.png"
                                    alt="linkedin" border="0"></a>
                            <div style="width: 20px;height: 20px; background: transparent"></div>
                            <a style="width: 20px;height: 20px;" href="https://www.instagram.com/gtechmulearn/"><img
                                    style="width: 15px;height: 15px;" src="https://i.ibb.co/tJxZw29/insta.png"
                                    alt="insta" border="0"></a>
                            <div style="width: 20px;height: 20px; background: transparent"></div>
                            <a style="width: 20px;height: 20px;" href="https://twitter.com/GtechMulearn"><img
                                    style="width: 15px;height: 15px;" src="https://i.ibb.co/MCnV8jP/twitter.png"
                                    alt="twitter" border="0"></a>
                        </div>
                        <p style="font-family: 'Poppins';line-height: 1.2;font-size: 13px;">µLearn Foundation |
                            Copyright © 2023. All rights reserved</p>
                    </center>
                </div>
                <div style="background: transparent;width: 100%;height: 20px;"></div>
            </center>
        </div>
    </center>
</body>

</html>
                        """
        contact_msg = strip_tags(html_message)
        # message = f"Reset your password with this link {domain}/reset-password?token={forget_user.id}"
        subject = "Password Reset Requested"
        send_mail(
            subject,
            contact_msg,
            email_host_user,
            to,
            fail_silently=False,
            html_message=html_message,
        )
        return CustomResponse(
            general_message="Forgot Password Email Send Successfully"
        ).get_success_response()


class ResetPasswordVerifyTokenAPI(APIView):
    def post(self, request, token):
        if not (forget_user := ForgotPassword.objects.filter(id=token).first()):
            return CustomResponse(
                general_message="Invalid Token"
            ).get_failure_response()
        current_time = DateTimeUtils.get_current_utc_time()

        if forget_user.expiry > current_time:
            muid = forget_user.user.mu_id
            return CustomResponse(response={"muid": muid}).get_success_response()
        else:
            forget_user.delete()
            return CustomResponse(
                general_message="Link is expired"
            ).get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        if not (forget_user := ForgotPassword.objects.filter(id=token).first()):
            return CustomResponse(
                general_message="Invalid Token"
            ).get_failure_response()
        current_time = DateTimeUtils.get_current_utc_time()
        if forget_user.expiry > current_time:
            return self.save_password(request, forget_user)
        forget_user.delete()
        return CustomResponse(general_message="Link is expired").get_failure_response()

    def save_password(self, request, forget_user):
        new_password = request.data.get("password")
        hashed_pwd = make_password(new_password)
        forget_user.user.password = hashed_pwd
        forget_user.user.save()
        forget_user.delete()
        return CustomResponse(
            general_message="New Password Saved Successfully"
        ).get_success_response()


class UserInviteAPI(APIView):
    def post(self, request):
        email = request.data.get("email")
        if User.objects.filter(email=email).exists():
            return CustomResponse(
                general_message="User already exist"
            ).get_failure_response()

        email_host_user = decouple.config("EMAIL_HOST_USER")
        to = [email]
        domain = decouple.config("FR_DOMAIN_NAME")
        message = f"Hi, \n\nYou have been invited to join the MuLearn community. Please click on the link below to join.\n\n{domain}\n\nThanks,\nMuLearn Team"
        send_mail(
            "Invitation to join MuLearn",
            message,
            email_host_user,
            to,
            fail_silently=False,
        )
        return CustomResponse(
            general_message="Invitation sent successfully"
        ).get_success_response()