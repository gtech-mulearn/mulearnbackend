from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from .company_views import is_company_owner_or_admin, _get_company_for_user


class CompanyEventTemplateListCreateAPI(APIView):
    """PRD §8.3 — reusable structure for recurring company event types (recruiting webinar, tech talk, hackathon)."""
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'], description="List the company's saved event templates.")
    def get(self, request):
        from db.company import CompanyEventTemplate

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Access denied. Verified company profile required.").get_failure_response(status_code=403)

        templates = CompanyEventTemplate.objects.filter(company=company).order_by("-created_at")
        data = [{
            "id": str(t.id), "title": t.title, "description": t.description,
            "event_type": t.event_type, "default_duration_minutes": t.default_duration_minutes,
        } for t in templates]
        return CustomResponse(response={"data": data}).get_success_response()

    @extend_schema(tags=['Dashboard - Events'], description="Save a new event template (owner or accepted co-admin only).")
    def post(self, request):
        from db.company import CompanyEventTemplate

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin to save templates.").get_failure_response(status_code=403)

        title = request.data.get("title")
        if not title:
            return CustomResponse(general_message="title is required.").get_failure_response()

        template = CompanyEventTemplate.objects.create(
            company=company,
            title=title,
            description=request.data.get("description"),
            event_type=request.data.get("event_type"),
            default_duration_minutes=request.data.get("default_duration_minutes"),
            created_by_id=user_id,
        )
        return CustomResponse(
            general_message="Event template saved successfully.",
            response={"id": str(template.id)},
        ).get_success_response()


class CompanyEventTemplateDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'], description="Delete a saved event template (owner or accepted co-admin only).")
    def delete(self, request, template_id):
        from db.company import CompanyEventTemplate

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin to delete templates.").get_failure_response(status_code=403)

        template = CompanyEventTemplate.objects.filter(id=template_id, company=company).first()
        if not template:
            return CustomResponse(general_message="Template not found.").get_failure_response(status_code=404)
        template.delete()
        return CustomResponse(general_message="Event template deleted successfully.").get_success_response()
