import decouple
import requests
from django.core.mail import send_mail
from django.db.models import Q
from django.utils.html import strip_tags
from rest_framework.views import APIView

from api.integrations.kkem.kkem_serializer import KKEMAuthorization
from db.organization import Country, Department, District, Organization, State, Zone
from db.task import InterestGroup
from db.user import Role, User
from utils.response import CustomResponse
from utils.types import OrganizationType

from . import serializers


class LearningCircleUserViewAPI(APIView):
    def post(self, request):
        mu_id = request.headers.get("muid")
        user = User.objects.filter(mu_id=mu_id).first()
        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()
        serializer = serializers.LearningCircleUserSerializer(user)
        id, mu_id, first_name, last_name, email, phone = serializer.data.values()
        name = f"{first_name}{last_name or ''}"
        return CustomResponse(
            response={
                "id": id,
                "mu_id": mu_id,
                "name": name,
                "email": email,
                "phone": phone,
            }
        ).get_success_response()


class RegisterDataAPI(APIView):
    def post(self, request):
        data = request.data
        jsid = request.data.get("jsid", None)
        integration = request.data.get("integration", None)

        create_user = serializers.RegisterSerializer(
            data=data, context={"request": request}
        )

        if not create_user.is_valid():
            return CustomResponse(
                message=create_user.errors, general_message="Invalid fields"
            ).get_failure_response()

        user_obj, password = create_user.save()
        auth_domain = decouple.config("AUTH_DOMAIN")
        response = requests.post(
            f"{auth_domain}/api/v1/auth/user-authentication/",
            data={"emailOrMuid": user_obj.mu_id, "password": password},
        )
        response = response.json()
        if response.get("statusCode") != 200:
            return CustomResponse(
                message=response.get("message")
            ).get_failure_response()
        res_data = response.get("response")
        access_token = res_data.get("accessToken")
        refresh_token = res_data.get("refreshToken")

        response = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
        }

        if jsid and integration:
            request.data["verified"] = True
            serialized_set = KKEMAuthorization(
                data=request.data, context={"type": "register"}
            )

            if not serialized_set.is_valid():
                return CustomResponse(
                    general_message=serialized_set.errors
                ).get_failure_response()

            serialized_set.save()
            response["dwms"] = serialized_set.data

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

        <div style="width: 400px; height: 800px;">
            <center>

                <img style="width: 400px;height: 220px;" src="https://iili.io/HQFW5rB.png" alt="HLi9NHP.md.png"
                    border="0">

                <div style="background: transparent;width: 100%;">
                    <center>
                        <h1 style="color: black;font-family: 'Poppins';font-weight: 600;font-size:26px;">YOUR TICKET TO µFAM IS HERE!</h1>
                        <P style="color: rgb(65, 64, 64);font-family: 'Poppins';line-height: 1.3;font-size: 13px;">Hey
                            there! A hearty welcome to the MuLearn Family.<br>
                            We are delighted to have you on board and we hereby acknowledge as well as appreciate your
                            interest to join our community and to take part in our initiatives.<br>

                            Your personal µid is provided below:
                        </P>
                        <div style="width: 100%;height: 10px;background: transparent;"></div>

                        <a 
                            style="display: flex; background-color: #EADCFF;border-radius: 28px;width: fit-content;">
                            <p style="padding-left: 20px; padding-right: 20px;font-family: 'Poppins';line-height: 1.2;font-size: 13px;">{user_obj.mu_id}</p>
                  
                        </a>

                        <div style="width: 100%;height: 10px;background: transparent;"></div>
                        <p style="color: black;font-family: 'Poppins';line-height: 1.3;font-size: 13px;">Stay tuned for
                            our events and notifications. Remember, you are not just any learner; you're a
                            MuLearner😉.<br><br>Happy Learning!</p>
                    </center>
                </div>
                <div style="background: transparent;width: 100%;height: 40px;"></div>
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
        email_host_user = decouple.config("EMAIL_HOST_USER")
        from_mail = decouple.config("FROM_MAIL")
        to = [user_obj.email]
        contact_msg = strip_tags(html_message)
        subject = "YOUR TICKET TO µFAM IS HERE!"
        send_mail(
            subject,
            contact_msg,
            from_mail,
            to,
            fail_silently=False,
            html_message=html_message,
        )
        response["data"] = serializers.UserDetailSerializer(user_obj, many=False).data
        return CustomResponse(response=response).get_success_response()


class RoleAPI(APIView):
    def get(self, request):
        role = Role.objects.all()
        role_serializer_data = serializers.RoleSerializer(role, many=True).data
        return CustomResponse(
            response={"roles": role_serializer_data}
        ).get_success_response()


class DepartmentAPI(APIView):
    def get(self, request):
        department_serializer = Department.objects.all()
        department_serializer_data = serializers.DepartmentSerializer(
            department_serializer, many=True
        ).data
        return CustomResponse(
            response={"department": department_serializer_data}
        ).get_success_response()


class CountryAPI(APIView):
    def get(self, request):
        countries = Country.objects.all()
        serializer = serializers.CountrySerializer(countries, many=True)
        return CustomResponse(
            response={
                "countries": serializer.data,
            }
        ).get_success_response()


class StateAPI(APIView):
    def post(self, request):
        state = State.objects.filter(country_id=request.data.get("country"))
        serializer = serializers.StateSerializer(state, many=True)
        return CustomResponse(
            response={
                "states": serializer.data,
            }
        ).get_success_response()


class DistrictAPI(APIView):
    def post(self, request):
        district = District.objects.filter(zone__state_id=request.data.get("state"))
        serializer = serializers.DistrictSerializer(district, many=True)
        return CustomResponse(
            response={
                "districts": serializer.data,
            }
        ).get_success_response()


class CollegeAPI(APIView):
    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.COLLEGE.value),
            Q(district_id=request.data.get("district")),
        )
        department_queryset = Department.objects.all()
        college_serializer_data = serializers.OrgSerializer(
            org_queryset, many=True
        ).data
        department_serializer_data = serializers.OrgSerializer(
            department_queryset, many=True
        ).data
        return CustomResponse(
            response={
                "colleges": college_serializer_data,
                "departments": department_serializer_data,
            }
        ).get_success_response()


class CompanyAPI(APIView):
    def get(self, request):
        company_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMPANY.value
        )
        company_serializer_data = serializers.OrgSerializer(
            company_queryset, many=True
        ).data
        return CustomResponse(
            response={"companies": company_serializer_data}
        ).get_success_response()


class CommunityAPI(APIView):
    def get(self, request):
        community_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMMUNITY.value
        )
        community_serializer_data = serializers.OrgSerializer(
            community_queryset, many=True
        ).data
        return CustomResponse(
            response={"communities": community_serializer_data}
        ).get_success_response()


class AreaOfInterestAPI(APIView):
    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        aoi_serializer_data = serializers.AreaOfInterestAPISerializer(
            aoi_queryset, many=True
        ).data
        return CustomResponse(
            response={"aois": aoi_serializer_data}
        ).get_success_response()


class UserEmailVerificationAPI(APIView):
    def post(self, request):
        user_email = request.data.get("email")
        if user := User.objects.filter(email=user_email).first():
            return CustomResponse(
                general_message="This email already exists", response={"value": True}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="User email not exist", response={"value": False}
            ).get_success_response()


class UserCountryAPI(APIView):
    def get(self, request):
        country = Country.objects.all()
        if country is None:
            return CustomResponse(
                general_message="No data available"
            ).get_success_response()
        country_serializer = serializers.UserCountrySerializer(country, many=True).data
        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):
    def get(self, request):
        country_name = request.data.get("country")

        country_object = Country.objects.filter(name=country_name).first()
        if country_object is None:
            return CustomResponse(
                general_message="No country data available"
            ).get_success_response()

        state_object = State.objects.filter(country_id=country_object).all()
        if len(state_object) == 0:
            return CustomResponse(
                general_message="No state data available for given country"
            ).get_success_response()

        state_serializer = serializers.UserStateSerializer(state_object, many=True).data
        return CustomResponse(response=state_serializer).get_success_response()


class UserZoneAPI(APIView):
    def get(self, request):
        state_name = request.data.get("state")

        state_object = State.objects.filter(name=state_name).first()
        if state_object is None:
            return CustomResponse(
                general_message="No state data available"
            ).get_success_response()

        zone_object = Zone.objects.filter(state_id=state_object).all()
        if len(zone_object) == 0:
            return CustomResponse(
                general_message="No zone data available for given country"
            ).get_success_response()

        zone_serializer = serializers.UserZoneSerializer(zone_object, many=True).data
        return CustomResponse(response=zone_serializer).get_success_response()
