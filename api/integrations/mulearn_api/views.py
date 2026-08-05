from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.user import User
from db.task import TaskList, KarmaActivityLog
from utils.response import CustomResponse

class ExternalTaskVerificationAPI(APIView):
    def get(self, request):
        muid = request.query_params.get('muid')
        email = request.query_params.get('email')
        hashtag = request.query_params.get('hashtag')

        if not all([muid, email, hashtag]):
            return CustomResponse(general_message=["The 'muid', 'email', and 'hashtag' query parameters are required."]).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.every.get(muid=muid, email=email)
        except User.DoesNotExist:
            return CustomResponse(general_message=["The user with the specified muid and email does not exist."]).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        try:
            task = TaskList.objects.get(hashtag=hashtag)
        except TaskList.DoesNotExist:
            return CustomResponse(general_message=["The task with the specified hashtag does not exist."]).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        log = KarmaActivityLog.objects.filter(
            user=user,
            task=task,
            appraiser_approved=True
        ).order_by('-updated_at').first()

        if log:
            verified = True
            verified_at = log.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ') if log.updated_at else None
        else:
            verified = False
            verified_at = None

        return CustomResponse(response={
            "verified": verified,
            "verified_at": verified_at,
        }).get_success_response()
