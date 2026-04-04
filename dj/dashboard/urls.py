from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('workflow/<str:workflow_id>/', views.workflow_detail, name='workflow_detail'),
    path('chat-history/', views.chat_history, name='chat_history'),
    path('mcp/toggle/', views.mcp_toggle, name='mcp_toggle'),
    # ChromaDB
    path('chromadb/', views.chromadb_index, name='chromadb_index'),
    path('chromadb/api/create/', views.chromadb_create, name='chromadb_create'),
    path('chromadb/api/update/<str:doc_id>/', views.chromadb_update, name='chromadb_update'),
    path('chromadb/api/delete/<str:doc_id>/', views.chromadb_delete, name='chromadb_delete'),
    path('chromadb/api/bulk-delete/', views.chromadb_bulk_delete, name='chromadb_bulk_delete'),
    path('chromadb/api/get/<str:doc_id>/', views.chromadb_get, name='chromadb_get'),
    path('chromadb/api/export/', views.chromadb_export, name='chromadb_export'),
    path('chromadb/api/whatsapp/', views.chromadb_whatsapp, name='chromadb_whatsapp'),
]
