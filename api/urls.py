from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TeamViewSet, TaskViewSet, CommentViewSet, ProjectInviteViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'invites', ProjectInviteViewSet, basename='invite')

urlpatterns = [
    path('', include(router.urls)),
]