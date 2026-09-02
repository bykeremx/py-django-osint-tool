from django.urls import path

from . import views

urlpatterns = [
    path("active/", views.active_jobs, name="scan_jobs_active"),
    path("cancel-all/", views.cancel_all_jobs, name="scan_jobs_cancel_all"),
    path("<str:job_id>/cancel/", views.cancel_job, name="scan_job_cancel"),
    path("<str:job_id>/status/", views.status, name="scan_job_status"),
]
