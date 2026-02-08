from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.Presentation.permissions import IsAdminUser
from src.Core.Application.Admin.Commands.ChangeUserRoleCommand import ChangeUserRoleCommand, ChangeUserRoleCommandHandler
from src.Core.Application.Admin.Queries.GetUsersQuery import GetUsersQuery, GetUsersQueryHandler

class ChangeUserRoleView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        command = ChangeUserRoleCommand(
            user_id=request.data.get('user_id'),
            new_role=request.data.get('new_role')
        )
        
        handler = ChangeUserRoleCommandHandler()
        result = handler.handle(command)
        
        if result.is_success:
            return Response({"message": "Role updated successfully"}, status=status.HTTP_200_OK)
            
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_400_BAD_REQUEST)

class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query = GetUsersQuery()
        handler = GetUsersQueryHandler()
        result = handler.handle(query)
        
        if result.is_success:
            return Response([vars(u) for u in result.data], status=status.HTTP_200_OK)
            
        return Response({"errors": [vars(e) for e in result.errors]}, status=status.HTTP_400_BAD_REQUEST)
