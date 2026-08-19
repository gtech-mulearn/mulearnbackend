import uuid
from datetime import timedelta

from decouple import config as decouple_config
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from django.db.models import Prefetch, Q
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.task import UserIgLink
from db.user import ForgotPassword, User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DateTimeUtils, DiscordWebhooks, send_template_mail
from . import dash_user_serializer
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s

BE_DOMAIN_NAME = decouple_config("BE_DOMAIN_NAME")


class UserInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Info.",
        responses={200: dash_user_serializer.UserSerializer},
    )
    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user_id = JWTUtils.fetch_user_id(request)
        user = (
            User.objects.prefetch_related(
                "user_domains", "user_endgoals", "user_role_link_user__role"
            )
            .filter(muid=user_muid)
            .first()
        )
        if user is not None:
            cache.set(f"db_user_{user_id}", user, timeout=60)
        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        try:
            cache.set(f"db_user_{user_muid}", user, timeout=60)
        except Exception:
            # Cache is an optimization; user info should still return when Redis is unavailable.
            pass

        response = dash_user_serializer.UserSerializer(user, many=False).data

        return CustomResponse(response=response).get_success_response()


class UserGetPatchDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Get Patch Delete.",
        responses={200: dash_user_serializer.UserDetailsSerializer},
    )
    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()

        if user is None:
            return CustomResponse(
                general_message="User Not Available"
            ).get_failure_response()

        serializer = dash_user_serializer.UserDetailsSerializer(user)

        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - User'], description="Delete User Get Patch Delete.",
        responses={200: dash_user_serializer.UserDetailsSerializer},
    )
    def delete(self, request, user_id):
        from django.db.models import ProtectedError
        from django.db import IntegrityError
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return CustomResponse(
                general_message="User deleted successfully"
            ).get_success_response()
        except User.DoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
        except (ProtectedError, IntegrityError) as e:
            return CustomResponse(
                general_message="Cannot delete user as they are linked to other data."
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - User'],
        description="Partially update User Get Patch Delete.",
        responses={200: dash_user_serializer.UserDetailsEditSerializer},
    )
    def patch(self, request, user_id):
        user = User.objects.get(id=user_id)

        request.data["admin"] = JWTUtils.fetch_user_id(request)

        serializer = dash_user_serializer.UserDetailsEditSerializer(
            user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            cache.delete(f"db_user_{user_id}")

            cache.delete(f"db_user_{user.muid}")

            DiscordWebhooks.general_updates(
                WebHookCategory.USER.value, WebHookActions.UPDATE.value, user_id
            )

            return CustomResponse(
                general_message="User Edited Successfully",
                response=serializer.data,
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    def normalize_list_param(self, values):
        """
        Supports:
        - repeated params: ?x=a&x=b
        - csv params: ?x=a,b
        - mixed: ?x=a&x=b,c
        """
        result = []
        for value in values:
            if value:
                result.extend(v.strip() for v in value.split(",") if v.strip())
        return result
    @role_required([RoleType.ADMIN.value])

    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User.",
        responses={200: dash_user_serializer.UserDashboardSerializer},
    )
    def get(self, request):
        user_queryset = User.objects.select_related(
            "wallet_user", "user_lvl_link_user", "user_lvl_link_user__level"
        ).all()

        # New Filters

        # karma filter
        minimum_karma = request.query_params.get("minKarma")
        if minimum_karma:
            try:
                minimum_karma = int(minimum_karma)
            except ValueError:
                return CustomResponse(
                    general_message="Invalid minKarma. It must be an integer."
                ).get_failure_response()

            user_queryset = user_queryset.filter(
                wallet_user__karma__gte=minimum_karma
            )

        # level filter
        level = request.query_params.get("level")
        if level:
            user_queryset = user_queryset.filter(
                user_lvl_link_user__level__name=level
            )

        # skill filter
        skills = self.normalize_list_param(request.query_params.getlist("skillIds"))
        if skills:
            user_queryset = user_queryset.filter(
                skill_progress__skill_id__in=skills
            ).distinct()
        
        # interest group filter
        interest_group_ids = self.normalize_list_param(request.query_params.getlist("interestGroupIds"))
        if interest_group_ids:
            user_queryset = user_queryset.filter(
                user_ig_link_user__ig_id__in=interest_group_ids
            ).distinct()

        # achievement filter
        achievement_ids = self.normalize_list_param(request.query_params.getlist("achievementIds"))
        if achievement_ids:
            user_queryset = user_queryset.filter(
                achievements__achievement_id__in=achievement_ids
            ).distinct()

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            [
                "muid",
                "full_name",
                "email",
                "mobile",
                "user_lvl_link_user__level__name",
            ],
            {
                "full_name": "full_name",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__name", 
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
    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Management C S V.",
        responses={200: dash_user_serializer.UserDashboardSerializer},
    )
    def get(self, request):
        user_queryset = User.objects.select_related(
            "wallet_user", "user_lvl_link_user", "user_lvl_link_user__level"
        ).all()

        serializer = dash_user_serializer.UserDashboardSerializer(
            user_queryset, many=True
        )

        return CommonUtils.generate_csv(serializer.data, "User")


class UserVerificationAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Verification.",
        responses={200: dash_user_serializer.UserVerificationSerializer},
    )
    def get(self, request):
        user_queryset = UserRoleLink.objects.select_related(
            "user",
            "user__district",
            "user__district__zone",
            "user__district__zone__state",
            "user__district__zone__state__country",
            "role",
        ).prefetch_related(
            "user__user_organization_link_user__org",
            "user__user_organization_link_user__org__district",
            "user__user_organization_link_user__department",
            "user__user_ig_link_user__ig",
            "user__mentor_profile",
            "user__company_profile",
        ).filter(
            verified=False
        )

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            search_fields=[
                "user__full_name",
                "user__mobile",
                "user__email",
                "user__muid",
                "role__title",
            ],
            sort_fields={
                "full_name": "user__full_name",
                "role_title": "role__title",
                "muid": "user__muid",
                "email": "user__email",
                "mobile": "user__mobile",
            },
        )
        serializer = dash_user_serializer.UserVerificationSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - User'],
        description="Partially update User Verification.",
        responses={200: dash_user_serializer.UserVerificationSerializer},
    )
    def patch(self, request, link_id):
        user = UserRoleLink.objects.get(id=link_id)

        user_serializer = dash_user_serializer.UserVerificationSerializer(
            user, data=request.data, partial=True
        )

        if not user_serializer.is_valid():
            return CustomResponse(
                general_message=user_serializer.errors
            ).get_failure_response()

        user_serializer.save()
        user_data = user_serializer.data

        DiscordWebhooks.general_updates(
            WebHookCategory.USER_ROLE.value,
            WebHookActions.UPDATE.value,
            user_data["user_id"],
        )

        send_template_mail(
            context=user_data,
            subject="Role request at μLearn!",
            address=["mentor_verification.html"],
        )

        return CustomResponse(
            response={"user_role_link": user_data}
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - User'], description="Delete User Verification.",
        responses={200: dash_user_serializer.UserVerificationSerializer},
    )
    def delete(self, request, link_id):
        link = UserRoleLink.objects.get(id=link_id)
        link.delete()

        return CustomResponse(
            general_message="Link deleted successfully"
        ).get_success_response()


class UserVerificationCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Verification C S V.",
        responses={200: dash_user_serializer.UserVerificationSerializer},
    )
    def get(self, request):
        user_queryset = UserRoleLink.objects.select_related(
            "user",
            "user__district",
            "user__district__zone",
            "user__district__zone__state",
            "user__district__zone__state__country",
            "role",
        ).prefetch_related(
            "user__user_organization_link_user__org",
            "user__user_organization_link_user__org__district",
            "user__user_organization_link_user__department",
            "user__user_ig_link_user__ig",
            "user__mentor_profile",
            "user__company_profile",
        ).filter(
            verified=False
        )

        serializer = dash_user_serializer.UserVerificationSerializer(
            user_queryset, many=True
        )
        return CommonUtils.generate_csv(serializer.data, "User")


class ForgotPasswordAPI(APIView):
    @extend_schema(tags=['Dashboard - User'], description="Create Forgot Password.",
        responses={200: OpenApiResponse(description="Forgot-password email sent")},
    )
    def post(self, request):
        email_muid = request.data.get("emailOrMuid")

        if not (
            user := User.objects.filter(
                Q(muid=email_muid) | Q(email=email_muid)
            ).first()
        ):
            return CustomResponse(
                general_message="User not exist"
            ).get_failure_response()

        created_at = DateTimeUtils.get_current_utc_time()
        expiry = created_at + timedelta(seconds=900)  # 15 minutes

        forget_user = ForgotPassword.objects.create(
            id=uuid.uuid4(), user=user, expiry=expiry, created_at=created_at
        )

        receiver_mail = user.email
        html_address = ["forgot_password.html"]
        context = {
            "email": receiver_mail,
            "token": forget_user.id,
        }

        send_template_mail(
            context=context,
            subject="Password Reset Requested",
            address=html_address,
        )

        return CustomResponse(
            general_message="Forgot Password Email Send Successfully"
        ).get_success_response()


class ResetPasswordVerifyTokenAPI(APIView):
    @extend_schema(tags=['Dashboard - User'], description="Create Reset Password Verify Token.",
        responses={200: inline_serializer(
            name='UserResetPasswordVerifyTokenResponse',
            fields={'muid': s.CharField()},
        )},
    )
    def post(self, request, token):
        if not (forget_user := ForgotPassword.objects.filter(id=token).first()):
            return CustomResponse(
                general_message="Invalid Token"
            ).get_failure_response()

        current_time = DateTimeUtils.get_current_utc_time()

        if forget_user.expiry > current_time:
            muid = forget_user.user.muid
            return CustomResponse(response={"muid": muid}).get_success_response()
        else:
            forget_user.delete()
            return CustomResponse(
                general_message="Link is expired"
            ).get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    @extend_schema(tags=['Dashboard - User'], description="Create Reset Password Confirm.",
        responses={200: OpenApiResponse(description="Password reset confirmation")},
    )
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


class UserProfilePictureView(APIView):
    # def get(self, request, user_id):
    #     user = User.objects.filter(id=user_id).first()

    #     if user is None:
    #         return CustomResponse(
    #             general_message="No user data available"
    #         ).get_failure_response()
    #     image_path = f'user/profile/{user_id}.png'
    #     response = ImageResponse(path=image_path)
    #     if response.exists():
    #         return response.get_success_response()
    #     else:
    #         return CustomResponse(
    #             general_message="No Profile picture available"
    #         ).get_failure_response()

    @extend_schema(tags=['Dashboard - User'], description="Partially update User Profile Picture.",
        responses={200: dash_user_serializer.UserSerializer},
    )
    def patch(self, request):
        DiscordWebhooks.general_updates(
            WebHookCategory.USER_PROFILE.value,
            WebHookActions.UPDATE.value,
            JWTUtils.fetch_user_id(request),
        )
        return CustomResponse(
            general_message="Successfully updated"
        ).get_success_response()

    @extend_schema(tags=['Dashboard - User'], description="Create User Profile Picture.",
        responses={200: dash_user_serializer.UserSerializer},
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        user = User.objects.filter(id=user_id).first()

        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        pic = request.FILES.get("profile")

        if pic is None:
            return CustomResponse(
                general_message="No profile picture"
            ).get_failure_response()

        if not pic.content_type.startswith("image/"):
            return CustomResponse(
                general_message="Expected an image"
            ).get_failure_response()

        extention = ".png"  # os.path.splitext(pic.name)[1]
        fs = FileSystemStorage()
        filename = f"user/profile/{user_id}{extention}"
        if fs.exists(filename):
            fs.delete(filename)
        filename = fs.save(filename, pic)
        file_url = fs.url(filename)
        uploaded_file_url = f"{BE_DOMAIN_NAME}{file_url}"

        return CustomResponse(
            response={"user_id": user.id, "profile_pic": uploaded_file_url}
        ).get_success_response()


class UserAddOrgAPI(APIView):
    @extend_schema(
        tags=['Dashboard - User'],
        description="Create User Add Org.",
        request=dash_user_serializer.UserOrgLinkSerializer,
        responses={200: dash_user_serializer.UserOrgLinkSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()
        serializer = dash_user_serializer.UserOrgLinkSerializer(
            data=request.data, context={"user": user}
        )
        if serializer.is_valid():
            org_link = serializer.save()
            if not org_link or isinstance(org_link, str):
                return CustomResponse(
                    general_message="organisation linked successfully"
                ).get_success_response()

            try:
                cache.delete(f"db_user_{user_id}")
                cache.delete(f"db_user_{user.muid}")
            except Exception:
                pass

            return CustomResponse(
                general_message="organisation linked successfully",
                response={
                    "organization_link": dash_user_serializer.GetUserLinkSerializer(
                        org_link
                    ).data,
                },
            ).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Add Org.",
        responses={200: dash_user_serializer.GetUserLinkSerializer},
    )
    def get(self, request):
        user = User.objects.filter(id=JWTUtils.fetch_user_id(request)).first()
        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        links = UserOrganizationLink.objects.filter(
            user=user, org__org_type=OrganizationType.COLLEGE.value
        ).order_by("-created_at", "-id").select_related("org", "department")[:1]
        serializer = dash_user_serializer.GetUserLinkSerializer(
            instance=links, many=True
        )
        return CustomResponse(response=serializer.data).get_success_response()


class UserSearchAPI(APIView):
    @extend_schema(
        tags=['Dashboard - User'],
        description="Retrieve User Search.",
        responses={200: dash_user_serializer.UserBasicDetailsSerializer},
    )
    def get(self, request):
        role = request.query_params.get("role")
        ig_id = request.query_params.get("ig_id")
        org_id = request.query_params.get("org_id")

        queryset = (
            User.objects.all()
            .select_related("wallet_user")
            .prefetch_related(
                "user_settings_user",
                Prefetch(
                    "user_ig_link_user",
                    queryset=UserIgLink.objects.select_related("ig").only(
                        "user_id", "ig__id", "ig__name"
                    ),
                ),
                Prefetch(
                    "user_organization_link_user",
                    queryset=UserOrganizationLink.objects.select_related("org").only(
                        "user_id", "org__id", "org__title", "org__code", "org__org_type"
                    ),
                ),
            )
            .order_by("-wallet_user__karma")
        )
        if role:
            queryset = queryset.filter(
                user_role_link_user__role__title=role,
                user_role_link_user__verified=True,
            )
        if ig_id:
            queryset = queryset.filter(user_ig_link_user__ig_id=ig_id)

        if org_id:
            queryset = queryset.filter(user_organization_link_user__org_id=org_id)

        queryset = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=[
                "full_name",
                "muid",
            ],
        )
        serializer = dash_user_serializer.UserBasicDetailsSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )


class UserPreferencesAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - User'], description="Retrieve User Preferences.",
        responses={200: dash_user_serializer.UserSerializer},
    )
    def get(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))

        response = {
            "interested_in_work": user.interested_in_work,
            "interested_in_gig_work": user.interested_in_gig_work,
        }

        return CustomResponse(response=response).get_success_response()

    @extend_schema(tags=['Dashboard - User'], description="Partially update User Preferences.",
        responses={200: dash_user_serializer.UserSerializer},
    )
    def patch(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))

        interested_in_work = request.data.get("interested_in_work")
        interested_in_gig_work = request.data.get("interested_in_gig_work")

        if isinstance(interested_in_work, bool):
            user.interested_in_work = interested_in_work
        if isinstance(interested_in_gig_work, bool):
            user.interested_in_gig_work = interested_in_gig_work

        user.save()

        return CustomResponse(
            general_message="Preferences updated successfully"
        ).get_success_response()
