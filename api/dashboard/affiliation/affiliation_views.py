from rest_framework.views import APIView
from utils.permission import CustomizePermission,role_required,JWTUtils
from utils.types import RoleType
from .serializers import AffiliationReadSerializer, AffiliationCreateUpdateSerializer
from db.organization import OrgAffiliation
from utils.response import CustomResponse
from utils.utils import CommonUtils

class AffiliationView(APIView):
  authentication_classes = [CustomizePermission]


  def get(self,request):
    all_affiliations = OrgAffiliation.objects.all()
    pager_ = CommonUtils.get_paginated_queryset(all_affiliations,request,['title'])
    serial_ = AffiliationReadSerializer(pager_.get('queryset'),many=True)
    # serial_.is_valid()
    return CustomResponse(response=serial_.data).get_success_response()
  
  @role_required([RoleType.ADMIN.value])
  def post(self,request):
    user_id = JWTUtils.fetch_user_id(request)
    
    serial_ = AffiliationCreateUpdateSerializer(data=request.data,context={'user_id':user_id})

    if serial_.is_valid():
        serial_.save()

        return CustomResponse(
            general_message=f"{request.data.get('title')} added successfully"
        ).get_success_response()

    return CustomResponse(
        general_message=serial_.errors
    ).get_failure_response()

  @role_required([RoleType.ADMIN.value])
  def put(self,request,affiliation_id):
    user_id = JWTUtils.fetch_user_id(request)
    affiliation = OrgAffiliation.objects.filter(id=affiliation_id).first()

    if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation"
            ).get_failure_response()

    serializer = AffiliationCreateUpdateSerializer(
        affiliation,
        data=request.data,
        context={
            "user_id": user_id
        }
    )
    if serializer.is_valid():
      serializer.save()

      return CustomResponse(
          general_message=f"{affiliation.title} Edited Successfully"
      ).get_success_response()

    return CustomResponse(
        message=serializer.errors
    ).get_failure_response()

  @role_required([RoleType.ADMIN.value])
  def delete(self,request,affiliation_id):
    user_id = JWTUtils.fetch_user_id(request)
    affiliation = OrgAffiliation.objects.filter(id=affiliation_id).first()

    if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation"
            ).get_failure_response()
    affiliation.delete()
    return CustomResponse(
          general_message=f"{affiliation.title} Deleted Successfully"
      ).get_success_response()