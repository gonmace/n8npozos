from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('workflow/<str:workflow_id>/', views.workflow_detail, name='workflow_detail'),
    path('chat-history/', views.chat_history, name='chat_history'),
]
