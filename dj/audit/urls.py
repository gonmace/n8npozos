from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_index, name='audit_index'),
    path('update-prompt/', views.audit_update_prompt, name='audit_update_prompt'),
    path('update-node-prompt/', views.audit_update_node_prompt, name='audit_update_node_prompt'),
    path('delete-rows/', views.audit_delete_rows, name='audit_delete_rows'),
    path('list-chats/', views.audit_list_chats, name='audit_list_chats'),
    path('preview-json/', views.audit_preview_json, name='audit_preview_json'),
    path('run-script/', views.audit_run_script, name='audit_run_script'),
    path('run-selected/', views.audit_run_selected, name='audit_run_selected'),
    path('script-output/<str:job_id>/', views.audit_script_output, name='audit_script_output'),
    path('script-monitor/<str:job_id>/', views.audit_script_monitor, name='audit_script_monitor'),
    path('script-send-select/', views.audit_script_send_select, name='audit_script_send_select'),
    path('script-cancel/<str:job_id>/', views.audit_script_cancel, name='audit_script_cancel'),
]
