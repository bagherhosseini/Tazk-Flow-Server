# models.py
from django.db import models
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q

class Projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold')
    ], db_index=True)
    task_statuses = models.JSONField(default=list(['Todo', 'In Progress', 'Done']))
    created_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    team = models.ForeignKey('Teams', on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'Projects'

class Teams(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        db_table = 'Teams'

class TeamMembers(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Teams, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=255, db_index=True)
    role = models.CharField(max_length=10, choices=[
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member')
    ])

    class Meta:
        db_table = 'TeamMembers'
        unique_together = ('team', 'user_id')

class ProjectInvites(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Teams, on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=[
        ('admin', 'Admin'),
        ('member', 'Member')
    ])
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined')
        ],
        default='pending'
    )
    invited_by = models.CharField(max_length=255)  # Clerk user_id of inviter
    invited_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ProjectInvites'
        # Allow multiple invites to same email (for re-inviting after decline)
        indexes = [
            models.Index(fields=['email', 'status']),
        ]

class Tasks(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ])
    due_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    project = models.ForeignKey(Projects, on_delete=models.PROTECT, null=True, blank=True)
    assigned_to = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True)
    tags = models.JSONField()

    def clean(self):
        if self.project and self.status not in self.project.task_statuses:
            raise ValidationError({
                'status': f'Status must be one of: {", ".join(self.project.task_statuses)}'
            })

    class Meta:
        db_table = 'Tasks'

class Comments(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255)

    class Meta:
        db_table = 'Comments'