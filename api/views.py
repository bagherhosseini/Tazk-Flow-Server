import os
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import Projects, Teams, TeamMembers, Tasks, Comments, ProjectInvites
from .serializers import (
    ProjectSerializer, TeamSerializer, TeamMemberSerializer,
    TaskSerializer, CommentSerializer, TaskWithProjectSerializer,
    ProjectDetailSerializer, ProjectBasicSerializer, InviteResponseSerializer,
    InviteRequestSerializer, ProjectInviteSerializer 
)
from clerk_backend_api import Clerk
from django.utils import timezone


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'basic_projects':
            return ProjectBasicSerializer
        return ProjectSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        team_memberships = TeamMembers.objects.filter(user_id=user_id).values_list('team_id', flat=True)
        return Projects.objects.filter(team_id__in=team_memberships)

    @action(detail=False, methods=['GET'])
    def basic_projects(self, request):
        """Get basic project information with member details"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "projects": serializer.data
        })

    @action(detail=False, methods=['GET'])
    def user_projects(self, request):
        """Get projects where the user is a member"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "projects": serializer.data
        })

    def perform_create(self, serializer):
        team_id = self.request.data.get('team')
        if not team_id:
            current_date = datetime.now().strftime("%Y-%m-%d")
            team = Teams.objects.create(
                name=f"Team for {self.request.data.get('name', 'Unnamed Project')} ({current_date})",
                description=f"Auto-generated team for project: {self.request.data.get('name', 'Unnamed Project')} ({current_date})"
            )
            TeamMembers.objects.create(
                team=team,
                user_id=self.request.user.id,
                role='owner'
            )
            serializer.save(team=team)
        else:
            serializer.save()


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return TaskWithProjectSerializer
        return TaskSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        team_memberships = TeamMembers.objects.filter(user_id=user_id).values_list('team_id', flat=True)
        user_projects = Projects.objects.filter(team_id__in=team_memberships).values_list('id', flat=True)
        
        return Tasks.objects.filter(
            Q(assigned_to=user_id) |
            Q(created_by=user_id) |
            Q(project_id__in=user_projects)
        ).select_related('project').distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)

    @action(detail=False, methods=['GET'])
    def personal_tasks(self, request):
        """Get tasks that aren't associated with any project"""
        user_id = self.request.user.id
        tasks = Tasks.objects.filter(
            Q(assigned_to=user_id) |
            Q(created_by=user_id),
            project__isnull=True
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response({
            "tasks": serializer.data
        })

    @action(detail=False, methods=['GET'])
    def project_tasks(self, request):
        user_id = request.user.id
        team_memberships = TeamMembers.objects.filter(user_id=user_id).values_list('team_id', flat=True)
        user_projects = Projects.objects.filter(team_id__in=team_memberships).values_list('id', flat=True)
        
        tasks = Tasks.objects.filter(
            project_id__in=user_projects
        ).select_related('project')
        
        serializer = self.get_serializer(tasks, many=True)
        return Response({
            "tasks": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def user_visible_tasks(self, request):
        user_id = request.user.id
        
        # Get personal tasks (no project)
        personal_tasks = Tasks.objects.filter(
            Q(assigned_to=user_id) | Q(created_by=user_id),
            project__isnull=True
        )
        
        # Get projects and their tasks
        team_memberships = TeamMembers.objects.filter(user_id=user_id).values_list('team_id', flat=True)
        projects = Projects.objects.filter(team_id__in=team_memberships)
        
        project_tasks_data = []
        for project in projects:
            project_data = ProjectDetailSerializer(project).data
            project_tasks = Tasks.objects.filter(
                project=project,
                assigned_to=user_id
            )
            project_data['tasks'] = TaskSerializer(project_tasks, many=True).data
            if project_tasks.exists():  # Only include projects that have tasks assigned to the user
                project_tasks_data.append(project_data)
        
        response_data = {
            "personal_tasks": TaskSerializer(personal_tasks, many=True).data,
            "project_tasks": project_tasks_data
        }
        
        return Response(response_data)


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.user.id
        return Teams.objects.filter(teammembers__user_id=user_id)

    def perform_create(self, serializer):
        team = serializer.save()
        # Automatically add the creator as an admin
        TeamMembers.objects.create(
            team=team,
            user_id=self.request.user.id,
            role='admin'
        )


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.user.id
        # Get all tasks visible to the user
        visible_tasks = TaskViewSet(request=self.request).get_queryset()
        return Comments.objects.filter(task__in=visible_tasks)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class ProjectInviteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['POST'])
    def invite_user(self, request):
        serializer = InviteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        project_id = serializer.validated_data['project_id']
        role = serializer.validated_data['role']

        try:
            project = Projects.objects.get(id=project_id)
            requesting_user_member = TeamMembers.objects.get(
                team=project.team,
                user_id=request.user.id
            )
            if requesting_user_member.role != 'admin' and role == 'owner':
                return Response(
                    {'error': 'Only admin users can send invites'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except (Projects.DoesNotExist, TeamMembers.DoesNotExist):
            return Response(
                {'error': 'Project not found or you do not have access'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is already a team member
        clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))
        try:
            users = clerk.users.list()
            invited_user = next(
                (user for user in users if user.email_addresses 
                and user.email_addresses[0].email_address == email),
                None
            )
            
            if invited_user:
                existing_member = TeamMembers.objects.filter(
                    team=project.team,
                    user_id=invited_user.id
                ).exists()

                if existing_member:
                    return Response(
                        {'error': 'User is already a member of this project'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for pending invites
                pending_invite = ProjectInvites.objects.filter(
                    team=project.team,
                    email=email,
                    status='pending'
                ).exists()

                if pending_invite:
                    return Response(
                        {'error': 'User already has a pending invite'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create new invite
            invite = ProjectInvites.objects.create(
                team=project.team,
                email=email,
                role=role,
                invited_by=request.user.id
            )

            return Response({
                'message': 'Invitation sent successfully',
                'invite_id': invite.id
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def pending_invites(self, request):
        """Get all pending invites for the current user's email"""
        # Get user's email from Clerk
        clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))
        try:
            user = clerk.users.get(user_id=request.user.id)
            user_email = user.email_addresses[0].email_address if user.email_addresses else None
            
            if not user_email:
                return Response(
                    {'error': 'No email found for user'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invites = ProjectInvites.objects.filter(
                email=user_email,
                status='pending'
            ).select_related('team')

            # Custom response with project details
            invite_data = []
            for invite in invites:
                project = Projects.objects.filter(team=invite.team).first()
                if project:
                    invite_data.append({
                        'invite_id': invite.id,
                        'project_id': project.id,
                        'project_name': project.name,
                        'team_id': invite.team.id,
                        'team_name': invite.team.name,
                        'role': invite.role,
                        'invited_at': invite.invited_at
                    })

            return Response({'invites': invite_data})

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['POST'])
    def respond_to_invite(self, request):
        """Accept or decline an invite"""
        serializer = InviteResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        invite_id = serializer.validated_data['invite_id']
        response = serializer.validated_data['response']

        try:
            # Get user's email from Clerk
            clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))
            user = clerk.users.get(user_id=request.user.id)
            user_email = user.email_addresses[0].email_address if user.email_addresses else None

            invite = ProjectInvites.objects.get(
                id=invite_id,
                email=user_email,
                status='pending'
            )

            invite.status = response
            invite.responded_at = timezone.now()
            invite.save()

            if response == 'accepted':
                # Create team member record
                TeamMembers.objects.create(
                    team=invite.team,
                    user_id=request.user.id,
                    role=invite.role
                )

            return Response({
                'message': f'Invite {response} successfully'
            })

        except ProjectInvites.DoesNotExist:
            return Response(
                {'error': 'Invite not found or already processed'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )