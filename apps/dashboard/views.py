from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
import re

from .models import UserProfile
from .serializers import UserProfileSerializer, UserProfileCreateSerializer, ProjectSerializer, ExperienceSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a profile to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the profile
        return obj.user == request.user


class UserProfileRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating user profiles.
    
    GET: Returns the authenticated user's profile
    PATCH: Updates the authenticated user's profile (partial updates supported)
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_object(self):
        """
        Get the user profile for the authenticated user.
        Create one if it doesn't exist.
        """
        user = self.request.user
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'email': user.email,
                'first_name': getattr(user, 'first_name', ''),
                'last_name': getattr(user, 'last_name', ''),
            }
        )
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the user's profile.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'message': 'Profile retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update the user's profile.
        Only updates the fields provided in the request.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """
        Full update is not allowed, only partial updates.
        """
        return Response({
            'success': False,
            'message': 'Full update not allowed. Use PATCH for partial updates.',
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_profile_summary(request):
    """
    Get a summary of the user's profile including counts.
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        summary_data = {
            'user_id': request.user.id,
            'username': request.user.username,
            'full_name': profile.get_full_name(),
            'email': profile.email,
            'has_bio': bool(profile.bio),
            'projects_count': profile.projects_count(),
            'experience_count': profile.experience_count(),
            'profile_completion': calculate_profile_completion(profile),
            'last_updated': profile.updated_at,
        }
        
        return Response({
            'success': True,
            'message': 'Profile summary retrieved successfully',
            'data': summary_data
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Profile not found',
        }, status=status.HTTP_404_NOT_FOUND)


def calculate_profile_completion(profile):
    """
    Calculate profile completion percentage based on filled fields.
    """
    total_fields = 7  # first_name, last_name, email, phone, bio, projects, experience
    completed_fields = 0
    
    if profile.first_name:
        completed_fields += 1
    if profile.last_name:
        completed_fields += 1
    if profile.email:
        completed_fields += 1
    if profile.phone:
        completed_fields += 1
    if profile.bio:
        completed_fields += 1
    if profile.projects:
        completed_fields += 1
    if profile.experience:
        completed_fields += 1
    
    return round((completed_fields / total_fields) * 100, 1)


# Legacy view functions for backward compatibility
@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def user_profile_view(request):
    """
    Legacy function-based view for user profile operations.
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            email=request.user.email,
            first_name=getattr(request.user, 'first_name', ''),
            last_name=getattr(request.user, 'last_name', ''),
        )
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response({
            'success': True,
            'message': 'Profile retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


# Granular CRUD Views for Bio, Projects, and Experience

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_bio(request):
    """
    Update only the bio field of the user's profile.
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            email=request.user.email,
            first_name=getattr(request.user, 'first_name', ''),
            last_name=getattr(request.user, 'last_name', ''),
        )
    
    bio_content = request.data.get('bio', '')
    profile.bio = bio_content
    profile.save()
    
    return Response({
        'success': True,
        'message': 'Bio updated successfully',
        'data': {'bio': profile.bio}
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def projects_list_create(request):
    """
    GET: List all projects for the authenticated user
    POST: Add a new project to the user's profile
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            email=request.user.email,
            first_name=getattr(request.user, 'first_name', ''),
            last_name=getattr(request.user, 'last_name', ''),
        )
    
    if request.method == 'GET':
        return Response({
            'success': True,
            'message': 'Projects retrieved successfully',
            'data': {
                'projects': profile.projects,
                'count': len(profile.projects)
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Validate the new project data
        project_serializer = ProjectSerializer(data=request.data)
        if project_serializer.is_valid():
            # Add the new project to the existing list
            new_project = project_serializer.validated_data
            if not profile.projects:
                profile.projects = []
            
            # Add an ID for the project for easier management
            project_id = len(profile.projects)
            new_project['id'] = project_id
            
            profile.projects.append(new_project)
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Project added successfully',
                'data': new_project
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': project_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def project_detail(request, project_id):
    """
    GET: Retrieve a specific project
    PUT: Update a specific project
    DELETE: Delete a specific project
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Find the project by ID
    project_index = None
    target_project = None
    
    for i, project in enumerate(profile.projects or []):
        if project.get('id') == project_id:
            project_index = i
            target_project = project
            break
    
    if target_project is None:
        return Response({
            'success': False,
            'message': 'Project not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        return Response({
            'success': True,
            'message': 'Project retrieved successfully',
            'data': target_project
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Validate the updated project data
        project_serializer = ProjectSerializer(data=request.data)
        if project_serializer.is_valid():
            updated_project = project_serializer.validated_data
            updated_project['id'] = project_id  # Preserve the ID
            
            # Replace the project at the found index
            profile.projects[project_index] = updated_project
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Project updated successfully',
                'data': updated_project
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': project_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Remove the project from the list
        profile.projects.pop(project_index)
        profile.save()
        
        return Response({
            'success': True,
            'message': 'Project deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def experience_list_create(request):
    """
    GET: List all experience entries for the authenticated user
    POST: Add a new experience entry to the user's profile
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            email=request.user.email,
            first_name=getattr(request.user, 'first_name', ''),
            last_name=getattr(request.user, 'last_name', ''),
        )
    
    if request.method == 'GET':
        return Response({
            'success': True,
            'message': 'Experience entries retrieved successfully',
            'data': {
                'experience': profile.experience,
                'count': len(profile.experience)
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Validate the new experience data
        experience_serializer = ExperienceSerializer(data=request.data)
        if experience_serializer.is_valid():
            # Add the new experience to the existing list
            new_experience = experience_serializer.validated_data
            if not profile.experience:
                profile.experience = []
            
            # Add an ID for the experience for easier management
            experience_id = len(profile.experience)
            new_experience['id'] = experience_id
            
            profile.experience.append(new_experience)
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Experience added successfully',
                'data': new_experience
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': experience_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def experience_detail(request, experience_id):
    """
    GET: Retrieve a specific experience entry
    PUT: Update a specific experience entry
    DELETE: Delete a specific experience entry
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Find the experience by ID
    experience_index = None
    target_experience = None
    
    for i, experience in enumerate(profile.experience or []):
        if experience.get('id') == experience_id:
            experience_index = i
            target_experience = experience
            break
    
    if target_experience is None:
        return Response({
            'success': False,
            'message': 'Experience not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        return Response({
            'success': True,
            'message': 'Experience retrieved successfully',
            'data': target_experience
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Validate the updated experience data
        experience_serializer = ExperienceSerializer(data=request.data)
        if experience_serializer.is_valid():
            updated_experience = experience_serializer.validated_data
            updated_experience['id'] = experience_id  # Preserve the ID
            
            # Replace the experience at the found index
            profile.experience[experience_index] = updated_experience
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Experience updated successfully',
                'data': updated_experience
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': experience_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Remove the experience from the list
        profile.experience.pop(experience_index)
        profile.save()
        
        return Response({
            'success': True,
            'message': 'Experience deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# Authentication endpoints

@csrf_exempt
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Get CSRF token for frontend authentication
    """
    return JsonResponse({
        'csrfToken': get_token(request)
    })


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """
    Authenticate user with email and password
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        
        print(f"Login attempt for email: {email}")  # Debug log
        
        if not email or not password:
            return JsonResponse({
                'success': False,
                'message': 'Email and password are required'
            }, status=400)
        
        # Try to find user by email (case insensitive)
        try:
            user = User.objects.get(email__iexact=email)
            print(f"Found user: {user.username}")  # Debug log
        except User.DoesNotExist:
            print(f"User not found for email: {email}")  # Debug log
            return JsonResponse({
                'success': False,
                'message': 'Invalid email or password'
            }, status=401)
        
        # Check if user is active
        if not user.is_active:
            print(f"User {user.username} is not active")  # Debug log
            return JsonResponse({
                'success': False,
                'message': 'Account is disabled'
            }, status=401)
        
        # Authenticate with username (since Django's default auth uses username)
        authenticated_user = authenticate(request, username=user.username, password=password)
        print(f"Authentication result: {authenticated_user is not None}")  # Debug log
        
        if authenticated_user is not None:
            login(request, authenticated_user)
            print(f"User {authenticated_user.username} logged in successfully")  # Debug log
            
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=authenticated_user,
                defaults={
                    'email': authenticated_user.email,
                    'first_name': getattr(authenticated_user, 'first_name', ''),
                    'last_name': getattr(authenticated_user, 'last_name', ''),
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': authenticated_user.id,
                    'username': authenticated_user.username,
                    'email': authenticated_user.email,
                    'first_name': authenticated_user.first_name,
                    'last_name': authenticated_user.last_name,
                }
            })
        else:
            print(f"Authentication failed for user: {user.username}")  # Debug log
            return JsonResponse({
                'success': False,
                'message': 'Invalid email or password'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during login'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def signup_view(request):
    """
    Create a new user account
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validation
        errors = {}
        
        if not username:
            errors['username'] = 'Username is required'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username already exists'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors['username'] = 'Username can only contain letters, numbers, and underscores'
            
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Please enter a valid email address'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'Email already registered'
            
        if not first_name:
            errors['first_name'] = 'First name is required'
        elif len(first_name) < 2:
            errors['first_name'] = 'First name must be at least 2 characters'
            
        if not last_name:
            errors['last_name'] = 'Last name is required'
        elif len(last_name) < 2:
            errors['last_name'] = 'Last name must be at least 2 characters'
            
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not re.search(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', password):
            errors['password'] = 'Password must contain uppercase, lowercase, and number'
            
        if phone and not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
            errors['phone'] = 'Please enter a valid phone number'
        
        if errors:
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=400)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            bio='',
            projects=[],
            experience=[]
        )
        
        # Log the user in immediately after signup
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'message': 'Account created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during signup'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    """
    Logout the current user
    """
    try:
        logout(request)
        return JsonResponse({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during logout'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def current_user_view(request):
    """
    Get current authenticated user information
    """
    if request.user.is_authenticated:
        return JsonResponse({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
    else:
        return JsonResponse({
            'message': 'User not authenticated'
        }, status=401)