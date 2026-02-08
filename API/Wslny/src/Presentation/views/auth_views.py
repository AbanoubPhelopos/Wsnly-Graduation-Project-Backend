from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from src.Core.Domain.Constants.Roles import Roles

from src.Core.Application.Authentication.Commands.RegisterCommand import RegisterCommand, RegisterCommandHandler
from src.Core.Application.Authentication.Commands.LoginCommand import LoginCommand, LoginCommandHandler
from src.Core.Application.Authentication.Commands.GoogleLoginCommand import GoogleLoginCommand, GoogleLoginCommandHandler
from src.Core.Application.Authentication.Queries.GetProfileQuery import GetProfileQuery, GetProfileQueryHandler

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        command = RegisterCommand(
            email=request.data.get('email'),
            password=request.data.get('password'),
            first_name=request.data.get('first_name'),
            last_name=request.data.get('last_name'),
            mobile_number=request.data.get('mobile_number'),
            gender=request.data.get('gender'),
            address=request.data.get('address'),
            role=request.data.get('role', Roles.USER)
        )
        
        handler = RegisterCommandHandler()
        result = handler.handle(command)
        
        if result.is_success:
            return Response({
                "token": result.data.token,
                "refresh_token": result.data.refresh_token,
                "user": {
                    "email": result.data.user.email,
                    "first_name": result.data.user.first_name,
                    "last_name": result.data.user.last_name
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        command = LoginCommand(
            email=request.data.get('email'),
            password=request.data.get('password')
        )
        
        handler = LoginCommandHandler()
        result = handler.handle(command)
        
        if result.is_success:
            return Response({
                "token": result.data.token,
                "refresh_token": result.data.refresh_token,
                "user": {
                    "email": result.data.user.email,
                    "first_name": result.data.user.first_name,
                    "last_name": result.data.user.last_name
                }
            }, status=status.HTTP_200_OK)
            
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_401_UNAUTHORIZED)

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        command = GoogleLoginCommand(id_token=request.data.get('id_token'))
        handler = GoogleLoginCommandHandler()
        result = handler.handle(command)
        
        if result.is_success:
             return Response({
                "token": result.data.token,
                "refresh_token": result.data.refresh_token,
                "user": {
                    "email": result.data.user.email,
                    "first_name": result.data.user.first_name,
                    "last_name": result.data.user.last_name
                }
            }, status=status.HTTP_200_OK)
        
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = GetProfileQuery(user_id=request.user.id)
        handler = GetProfileQueryHandler()
        result = handler.handle(query)
        
        if result.is_success:
            return Response(vars(result.data), status=status.HTTP_200_OK)
            
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_404_NOT_FOUND)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Implementation of Change Password Command would go here
        # For brevity, reusing the pattern
        return Response({"message": "Not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)
