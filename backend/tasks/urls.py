from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TagListView, VirtualTagListView
from .auth_views import login, logout, check

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    path('tags/', TagListView.as_view(), name='tag-list'),
    path('virtual-tags/', VirtualTagListView.as_view(), name='virtual-tag-list'),
    path('auth/login/', login, name='auth-login'),
    path('auth/logout/', logout, name='auth-logout'),
    path('auth/check/', check, name='auth-check'),
]
