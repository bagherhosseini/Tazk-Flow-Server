from rest_framework import serializers
from django.utils import timezone
from .models import Projects, Teams, TeamMembers, Tasks, Comments, ProjectInvites
from clerk_backend_api import Clerk
from django.conf import settings
import os


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teams
        fields = '__all__'
        read_only_fields = ('id',)


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMembers
        fields = '__all__'


class ProjectMemberSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    image_url = serializers.CharField()
    role = serializers.CharField()


class ProjectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasks
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        project = data.get('project', None)
        status = data.get('status', None)

        if project:
            if isinstance(project, int):
                try:
                    from .models import Projects
                    project = Projects.objects.get(id=project)
                except Projects.DoesNotExist:
                    raise serializers.ValidationError({
                        'project': 'Project does not exist.'
                    })

            project_statuses = project.task_statuses
            if not project_statuses:
                raise serializers.ValidationError({
                    'project': 'The project does not have defined task statuses.'
                })
            
            if status and status not in project_statuses:
                raise serializers.ValidationError({
                    'status': f'Status must be one of: {", ".join(project_statuses)}'
                })

            if not status:
                data['status'] = project_statuses[0]
        elif not status:
            data['status'] = 'Todo'

        return data


class ProjectBasicSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Projects
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def get_members(self, obj):
        try:
            # Get team members
            team_members = TeamMembers.objects.filter(team=obj.team)
            
            # Initialize Clerk client
            clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))
            
            members_data = []
            for member in team_members:
                try:
                    user = clerk.users.get(user_id=member.user_id)
                    members_data.append({
                        'user_id': user.id,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email_addresses[0].email_address if user.email_addresses else None,
                        'image_url': user.image_url,
                        'role': member.role
                    })
                except Exception as e:
                    print(f"Error fetching user {member.user_id}: {str(e)}")
                    continue
            
            return members_data
        except Exception as e:
            print(f"Error getting members: {str(e)}")
            return []


class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True, source='tasks_set')

    class Meta:
        model = Projects
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class TaskWithProjectSerializer(serializers.ModelSerializer):
    project = ProjectBasicSerializer(read_only=True)
    
    class Meta:
        model = Tasks
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        project = data.get('project', None)
        status = data.get('status', None)

        if project:
            project_statuses = project.task_statuses
            if not project_statuses:
                raise serializers.ValidationError({
                    'project': 'The project does not have defined task statuses.'
                })
            
            if status and status not in project_statuses:
                raise serializers.ValidationError({
                    'status': f'Status must be one of: {", ".join(project_statuses)}'
                })

            if not status:
                data['status'] = project_statuses[0]

        return data


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class ProjectWithTasksSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Projects
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def get_tasks(self, obj):
        # Get only tasks assigned to the current user
        user_id = self.context.get('request').user.id
        tasks = obj.tasks_set.filter(assigned_to=user_id)
        return TaskSerializer(tasks, many=True).data


class ProjectInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvites
        fields = '__all__'
        read_only_fields = ('id', 'invited_by', 'invited_at', 'responded_at', 'status')


class InviteRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    project_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=['owner', 'admin', 'member'], default='member')


class InviteResponseSerializer(serializers.Serializer):
    invite_id = serializers.UUIDField()
    response = serializers.ChoiceField(choices=['accepted', 'declined'])