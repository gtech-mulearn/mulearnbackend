"""
µLearn Backend – Mentor API Module
---------------------------------
Author: @anjanarajesh-00
License: MIT
Description:
A fully featured Django REST API for managing mentors within µLearn.
This module provides CRUD operations, validation, filtering,
searching, sorting, and pagination. Written for clarity and reusability.

You can integrate this directly into your µLearn backend.
"""

# ======================================================
# Imports
# ======================================================
from django.db import models
from rest_framework import serializers, generics, status, filters
from rest_framework.response import Response
from django.urls import path
from rest_framework.pagination import PageNumberPagination

# ======================================================
# Model: Mentor
# ======================================================
class Mentor(models.Model):
    """
    Mentor model defines the core structure of a mentor in µLearn.
    Each mentor has a name, area of expertise, contact details,
    and optional profile information for community discovery.
    """

    # Basic Info
    name = models.CharField(max_length=100, help_text="Full name of the mentor")
    expertise = models.CharField(max_length=150, help_text="Primary area of expertise")

    # Contact Info
    email = models.EmailField(unique=True, help_text="Email address (must be unique)")
    linkedin = models.URLField(blank=True, null=True, help_text="LinkedIn profile URL")

    # Additional Info
    bio = models.TextField(blank=True, null=True, help_text="Short biography or background")
    available = models.BooleanField(default=True, help_text="Mentor availability status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.expertise})"

    class Meta:
        ordering = ['name']
        verbose_name = "Mentor"
        verbose_name_plural = "Mentors"


# ======================================================
# Serializer: MentorSerializer
# ======================================================
class MentorSerializer(serializers.ModelSerializer):
    """
    Converts Mentor model instances to JSON and validates input data.
    """

    class Meta:
        model = Mentor
        fields = [
            'id',
            'name',
            'expertise',
            'email',
            'linkedin',
            'bio',
            'available',
            'created_at',
            'updated_at',
        ]

    # Custom validation example
    def validate_name(self, value):
        if len(value.split()) < 2:
            raise serializers.ValidationError("Please enter full name (first and last).")
        return value

    def validate_expertise(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Expertise must have at least 3 characters.")
        return value


# ======================================================
# Pagination Class
# ======================================================
class MentorPagination(PageNumberPagination):
    """
    Custom pagination for mentor list.
    """
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 20


# ======================================================
# Views
# ======================================================

class MentorListCreateView(generics.ListCreateAPIView):
    """
    View to list all mentors or create a new one.
    Includes filtering, search, and ordering capabilities.
    """
    queryset = Mentor.objects.all()
    serializer_class = MentorSerializer
    pagination_class = MentorPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'expertise', 'bio']
    ordering_fields = ['name', 'created_at']

    def create(self, request, *args, **kwargs):
        """
        Overridden create method to return a custom success message.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "🎉 Mentor successfully added!",
                "mentor": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class MentorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific mentor by ID.
    """
    queryset = Mentor.objects.all()
    serializer_class = MentorSerializer

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "🗑️ Mentor deleted successfully"}, status=status.HTTP_200_OK)


# ======================================================
# Extra Feature: Mentor Availability Toggle
# ======================================================
from rest_framework.decorators import api_view

@api_view(['POST'])
def toggle_availability(request, pk):
    """
    Endpoint to toggle the mentor's availability status.
    """
    try:
        mentor = Mentor.objects.get(pk=pk)
    except Mentor.DoesNotExist:
        return Response({"error": "Mentor not found"}, status=status.HTTP_404_NOT_FOUND)

    mentor.available = not mentor.available
    mentor.save()
    return Response({
        "message": f"Mentor '{mentor.name}' availability updated to {mentor.available}",
        "available": mentor.available,
    })


# ======================================================
# URL Configuration
# ======================================================
urlpatterns = [
    path('mentors/', MentorListCreateView.as_view(), name='mentor-list'),
    path('mentors/<int:pk>/', MentorDetailView.as_view(), name='mentor-detail'),
    path('mentors/<int:pk>/toggle/', toggle_availability, name='mentor-toggle'),
]


# ======================================================
# How to Integrate This File
# ======================================================
"""
Integration Steps:

1️⃣ Place this file in your main Django app (example: core/)
   Path: mulearn-backend/core/mentor_api.py

2️⃣ In your project’s main urls.py, import and include these URLs:
   from core.mentor_api import urlpatterns as mentor_urls
   urlpatterns += mentor_urls

3️⃣ Apply migrations:
   python manage.py makemigrations
   python manage.py migrate

4️⃣ Run the server:
   python manage.py runserver

5️⃣ Test the API:
   GET     /mentors/                → List mentors
   POST    /mentors/                → Add new mentor
   GET     /mentors/<id>/           → Get mentor details
   PUT     /mentors/<id>/           → Update mentor
   DELETE  /mentors/<id>/           → Delete mentor
   POST    /mentors/<id>/toggle/    → Toggle availability

✅ Example JSON for adding a mentor:
{
  "name": "Anjana Rajesh",
  "expertise": "AI & Backend Development",
  "email": "anjana@example.com",
  "linkedin": "https://linkedin.com/in/anjanarajesh",
  "bio": "Passionate mentor focusing on AI-driven learning tools",
  "available": true
}

🎯 Expected Output:
{
  "message": "🎉 Mentor successfully added!",
  "mentor": {
    "id": 1,
    "name": "Anjana Rajesh",
    "expertise": "AI & Backend Development",
    "email": "anjana@example.com",
    "linkedin": "https://linkedin.com/in/anjanarajesh",
    "bio": "Passionate mentor focusing on AI-driven learning tools",
    "available": true,
    "created_at": "2025-10-30T18:32:00Z",
    "updated_at": "2025-10-30T18:32:00Z"
  }
}
"""

# ======================================================
# End of File
# ======================================================
