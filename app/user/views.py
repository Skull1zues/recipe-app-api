"""
Views for the user API
"""
from rest_framework import generics
from user.serializers import UserSerializer
from rest_framework.views import APIView

class CreateUserView(generics.CreateAPIView):
    """Create a new useer in the system"""
    serializer_class = UserSerializer



    