import os

from django.db.models import Count, Sum, F, Case, When, Value, CharField
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from db.learning_circle import LearningCircle, UserCircleLink
from mulearnbackend.settings import BASE_DIR
from utils.response import CustomResponse
from utils.types import IntegrationType


class CommonAPI(APIView):
    def get(self, request, log_type):
        print("log type", log_type)
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)

        if os.path.exists(log_file_path):
            try:
                def file_iterator(file_path):
                    with open(file_path, 'rb') as log_file:
                        chunk_size = 8192
                        while True:
                            chunk = log_file.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk

                response = StreamingHttpResponse(file_iterator(log_file_path), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{log_type}.log"'
                return response
            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})


class ViewCommonAPI(APIView):
    def get(self, request, log_type):
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)

        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r') as log_file:
                    log_content = log_file.read()
                
                # You can return the log content as plain text or JSON, depending on your requirements.
                # For plain text response:
                return Response({'log_content': log_content}, content_type='text/plain')

                # For JSON response:
                # return Response({'log_content': log_content})

            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})

class ClearCommonAPI(APIView):
   def post(self,request,log_type):
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'w') as log_file:
                    log_file.truncate(0)
                
                return Response({'detail': f'{log_type} log cleared successfully'})

            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})

class LcDashboardAPI(APIView):

    def get(self, request):
        date = request.GET.get('date')
        if date:
            learning_circle_count = LearningCircle.objects.filter(created_at__gt=date).count()
            total_no_enrollment = UserCircleLink.objects.filter(lead=False, accepted=True, created_at__gt=date).count()
            circle_count_by_ig = LearningCircle.objects.filter(created_at__gt=date).values(
                ig_name=F('ig__name')).annotate(
                total_circles=Count('id'))
        else:
            learning_circle_count = LearningCircle.objects.all().count()
            total_no_enrollment = UserCircleLink.objects.filter(lead=False, accepted=True).count()
            circle_count_by_ig = LearningCircle.objects.all().values(ig_name=F('ig__name')).annotate(
                total_circles=Count('id'))
        return CustomResponse(response={'lc_count': learning_circle_count, 'total_enrollment': total_no_enrollment,
                                        'circle_count_by_ig': circle_count_by_ig}).get_success_response()


class LcReportAPI(APIView):

    def get(self, request):
        student_info = UserCircleLink.objects.filter(lead=False, accepted=True).values(
            first_name=F('user__first_name'),
            last_name=F('user__last_name'),
            muid=F('user__mu_id'),
            circle_name=F('circle__name'),
            circle_ig=F('circle__ig__name'),
            organisation=F('user__user_organization_link_user__org__title'),
            dwms_id=Case(
                When(
                    user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    then=F('user__integration_authorization_user__additional_field')
                ),
                default=Value(None, output_field=CharField()),
                output_field=CharField()
            )
        ).annotate(karam_earned=Sum('user__karma_activity_log_user__karma'))

        return CustomResponse(response=student_info).get_success_response()
