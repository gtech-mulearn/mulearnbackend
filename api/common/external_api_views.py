from functools import wraps
from django.core.cache import cache
from rest_framework.views import APIView

from db.launchpad import LaunchpadJobTasks
from db.user import User
from utils.response import CustomResponse
from .external_api_serializer import ExternalUserDetailsSerializer
from drf_spectacular.utils import extend_schema


def rate_limit(max_requests=100, time_window=60):
    """
    Rate limiting decorator for API views.
    
    Args:
        max_requests: Maximum number of requests allowed (default: 100)
        time_window: Time window in seconds (default: 60 seconds)
    
    Returns 429 if rate limit is exceeded.
    Uses Redis cache to track request counts per IP address.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(self, request, *args, **kwargs):
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            cache_key = f"rate_limit_external_api_{ip_address}"
            request_count = cache.get(cache_key, 0)
        
            if request_count >= max_requests:
                return CustomResponse(
                    general_message=f"Rate limit exceeded. Maximum {max_requests} requests per minute allowed."
                ).get_failure_response(http_status_code=429)
            if request_count == 0:
                cache.set(cache_key, 1, time_window)
            else:
                cache.incr(cache_key)
            return view_func(self, request, *args, **kwargs)
        
        return wrapped_view
    return decorator


class ExternalUserDetailsAPI(APIView):
    """
    External API endpoint for fetching basic user details.
    
    This endpoint is designed for external website integration.
    Public endpoint (no authentication required) that only returns public user profiles.
    
    Rate limited to 100 requests per minute per IP address.
    """

    @rate_limit(max_requests=100, time_window=60)
    @extend_schema(
        tags=['Common'],
        description="Retrieve External User Details.",
        responses={200: ExternalUserDetailsSerializer},
    )
    def get(self, request):
        """
        Fetch basic user details by muid.
        
        Query Parameters:
            muid (str): The unique mulearn user ID (format: username@mulearn)
        
        Returns:
            200: User details (if public profile)
            400: Missing muid parameter
            403: Private profile
            404: User not found
            429: Rate limit exceeded
        """
        muid = request.query_params.get("muid")
        
        if not muid:
            return CustomResponse(
                general_message="muid parameter is required"
            ).get_failure_response()
        
        try:
            user = (
                User.objects
                .select_related("wallet_user", "user_settings_user")
                .prefetch_related(
                    "user_organization_link_user__org",
                    "user_ig_link_user__ig"
                )
                .get(muid=muid)
            )
        except User.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response(http_status_code=404)
        
        try:
            is_public = user.user_settings_user.is_public
        except:
            is_public = False
        
        if not is_public:
            return CustomResponse(
                general_message="This user profile is private"
            ).get_failure_response(http_status_code=403)
        
        serializer = ExternalUserDetailsSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()


class ExternalTaskVerificationAPI(APIView):
    """
    Public API endpoint for verifying external task submissions.
    NO AUTHENTICATION REQUIRED - Public endpoint
    
    Query Parameters:
        muid (str): User's mulearn ID (e.g., 'john@mulearn')
        email (str): User's email address
        hashtag (str): Task hashtag (URL-encoded, e.g., '#mulearn-test')
    
    Returns:
        200: Task verified/found
        400: Missing required parameters
        404: Task/User not found
        429: Rate limit exceeded
    """

    @rate_limit(max_requests=100, time_window=60)
    @extend_schema(
        tags=['Common'],
        description="Verify External Task Submission (Public - No Auth Required)",
        responses={200: ExternalUserDetailsSerializer},
    )
    def get(self, request):
        """
        Verify if a user has submitted a valid task with the given hashtag.
        """
        muid = request.query_params.get("muid")
        email = request.query_params.get("email")
        hashtag = request.query_params.get("hashtag")
        
        # Validate required parameters
        if not muid or not email or not hashtag:
            return CustomResponse(
                general_message="'muid', 'email', and 'hashtag' query parameters are required"
            ).get_failure_response(http_status_code=400)
        
        try:
            # Find user by muid and email
            user = User.objects.get(muid=muid, email=email)
        except User.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response(http_status_code=404)
        
        try:
            task = LaunchpadJobTasks.objects.get(hashtags=hashtag)
            
            if not task.is_verified:
                return CustomResponse(
                    general_message="Task is not verified",
                    response={
                        "verified": False,
                        "verified_at": None
                    }
                ).get_success_response()
            
            return CustomResponse(
                general_message="Task verified successfully",
                response={
                    "verified": True,
                    "verified_at": task.updated_at.isoformat() if task.updated_at else None,
                    "task_id": task.id,
                    "task_description": task.task_description
                }
            ).get_success_response()
            
        except LaunchpadJobTasks.DoesNotExist:
            return CustomResponse(
                general_message="Task not found",
                response={
                    "verified": False,
                    "verified_at": None
                }
            ).get_failure_response(http_status_code=404)
            
        except Exception as e:
            return CustomResponse(
                general_message=f"Error verifying task: {str(e)}"
            ).get_failure_response(http_status_code=400)