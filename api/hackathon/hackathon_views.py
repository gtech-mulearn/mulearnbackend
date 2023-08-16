from datetime import datetime

from django.db.models import Q
from rest_framework.views import APIView

from db.hackathon import (
    Hackathon,
    HackathonForm,
    HackathonOrganiserLink,
    HackathonUserSubmission,
)
from db.organization import District, Organization
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import DEFAULT_HACKATHON_FORM_FIELDS, RoleType
from serializer import HackathonRetrievalSerializer, UpcomingHackathonRetrievalSerializer, \
    HackathonCreateUpdateDeleteSerializer, HackathonUpdateSerializer, HackathonPublishingSerializer, \
    HackathonInfoSerializer, HackathonUserSubmissionSerializer, ListApplicantsSerializer, \
    HackathonOrganiserSerializerRetrieval, HackathonOrganiserSerializer, HackathonFormSerializer, DistrictSerializer, \
    OrganisationSerializer


class HackathonManagementAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, hackathon_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if request.path.endswith("upcoming/"):
            hackathons_queryset = Hackathon.objects.filter(
                event_start__gt=datetime.now()
            ).all()
            serializer = UpcomingHackathonRetrievalSerializer(
                hackathons_queryset, many=True
            )
        elif hackathon_id:
            hackathons_queryset = Hackathon.objects.filter(id=hackathon_id).first()

            if hackathons_queryset is None:
                return CustomResponse(
                    general_message="Hackathon Does Not Exist"
                ).get_failure_response()
            serializer = HackathonRetrievalSerializer(
                hackathons_queryset
            )
        else:
            hackathons_queryset = Hackathon.objects.filter(
                Q(status="Published") | Q(hackathonorganiserlink__organiser_id=user_id)
            )
            serializer = HackathonRetrievalSerializer(
                hackathons_queryset, many=True, context={"user_id": user_id}
            )
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = HackathonCreateUpdateDeleteSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            instance = serializer.save()
            return CustomResponse(
                general_message="Hackathon Created",
                response={"hackathon_id": instance.id},
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        if hackathon is None:
            return CustomResponse(
                general_message="Hackathon Does Not Exist"
            ).get_failure_response()
        serializer = HackathonUpdateSerializer(
            hackathon, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Hackathon Updated"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        if hackathon is None:
            return CustomResponse(
                general_message="Hackathon Does Not Exist"
            ).get_failure_response()
        serializer = HackathonCreateUpdateDeleteSerializer()
        serializer.destroy(hackathon)
        return CustomResponse(
            general_message="Hackathon Deleted"
        ).get_success_response()


class HackathonPublishingAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def put(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        if hackathon is None:
            return CustomResponse(
                general_message="Hackathon Does Not Exist"
            ).get_failure_response()
        serializer = HackathonPublishingSerializer(
            hackathon, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Hackathon Updated"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class HackathonInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        serializer = HackathonInfoSerializer(
            hackathon, many=False, context={"request": request}
        )
        return CustomResponse(response=serializer.data).get_success_response()


class GetDefaultFieldsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        return CustomResponse(
            response=DEFAULT_HACKATHON_FORM_FIELDS
        ).get_success_response()


class HackathonSubmissionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = HackathonUserSubmissionSerializer(
            data=request.data, context={"request": request, "user_id": user_id}
        )
        if serializer.is_valid():
            instance = serializer.save()
            return CustomResponse(
                general_message="Hackathon Submission Successful",
                response={"hackathon_id": instance.id},
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class ListApplicantsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, hackathon_id=None):
        if hackathon_id:
            data = HackathonUserSubmission.objects.filter(hackathon__id=hackathon_id)
            if not data:
                return CustomResponse(
                    general_message="Hackathon Not Available"
                ).get_failure_response()
        else:
            data = HackathonUserSubmission.objects.all()

        serializer = ListApplicantsSerializer(data, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class HackathonOrganiserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, hackathon_id):
        hackathon_ids = HackathonOrganiserLink.objects.filter(
            hackathon__id=hackathon_id
        )
        serializer = HackathonOrganiserSerializerRetrieval(
            hackathon_ids, many=True
        )
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        if hackathon is None:
            return CustomResponse(
                general_message="Hackathon Does Not Exist"
            ).get_failure_response()
        serializer = HackathonOrganiserSerializer(
            data=request.data, context={"request": request, "hackathon": hackathon}
        )
        if serializer.is_valid():
            instance = serializer.save()
            return CustomResponse(
                general_message="Hackathon Organiser Added",
                response={"organiser_link_id": instance.id},
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, organiser_link_id):
        organiser = HackathonOrganiserLink.objects.filter(id=organiser_link_id).first()
        if organiser is None:
            return CustomResponse(
                general_message="Organiser Does Not Exist"
            ).get_failure_response()
        serializer = HackathonOrganiserSerializer()
        serializer.destroy(organiser)
        return CustomResponse(
            general_message="Organiser Deleted"
        ).get_success_response()


class ListOrganisations(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        organisations = Organization.objects.all()
        serializer = OrganisationSerializer(
            organisations, many=True
        )
        return CustomResponse(response=serializer.data).get_success_response()


class ListDistricts(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        districts = District.objects.all()
        serializer = DistrictSerializer(districts, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class ListHackathonFormAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, hackathon_id):
        hackathon = Hackathon.objects.filter(id=hackathon_id).first()
        if hackathon is None:
            return CustomResponse(
                general_message="Hackathon Does Not Exist"
            ).get_failure_response()
        hackathon_form = HackathonForm.objects.filter(hackathon=hackathon)
        serializer = HackathonFormSerializer(
            hackathon_form, many=True
        )
        return CustomResponse(response=serializer.data).get_success_response()
