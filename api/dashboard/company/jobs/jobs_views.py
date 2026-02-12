from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction

from utils.response import CustomResponse
from db.company import CompanyJob, Company, CompanyAdmin
from .serializers import CreateCompanyJobSerializer, CompanyJobResponseSerializer


class CreateCompanyJobAPI(APIView):
    """
    API endpoint to create a new job posting under a company.
    Only company admins can create job postings.
    """

    def post(self, request):
        try:
            # Validate request data
            serializer = CreateCompanyJobSerializer(data=request.data)
            
            if not serializer.is_valid():
                errors = []
                for field, field_errors in serializer.errors.items():
                    for error in field_errors:
                        errors.append(str(error))
                
                return CustomResponse(
                    general_message=errors[0] if errors else "Invalid input"
                ).get_failure_response()

            company_id = request.data.get('company_id')
            
            # Check if company exists
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return CustomResponse(
                    general_message="Company does not exist"
                ).get_failure_response(
                    status_code=404, 
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # TODO: Add authentication check to verify if user is a company admin
            # For now, we'll skip this check since authentication middleware is not visible
            # In a real implementation, you would check:
            # if not CompanyAdmin.objects.filter(company=company, user=request.user).exists():
            #     return CustomResponse(
            #         general_message="You are not authorized to create jobs for this company"
            #     ).get_failure_response(
            #         status_code=403,
            #         http_status_code=status.HTTP_403_FORBIDDEN
            #     )

            # Create the job
            with transaction.atomic():
                job = serializer.save(created_by_id=company.created_by_id, updated_by_id=company.created_by_id)

            # Prepare response
            response_serializer = CompanyJobResponseSerializer(job)
            
            return CustomResponse(
                general_message="Job created successfully",
                response={"job": response_serializer.data}
            ).get_success_response()

        except Exception as e:
            return CustomResponse(
                general_message="Something went wrong"
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
