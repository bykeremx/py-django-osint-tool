from django.urls import include, path

from .views import dashboard_view

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("dns-scan/", include("app.web.views.dns_scan.urls")),
    path("network-intel/", include("app.web.views.network.urls")),
    path("image-osint/", include("app.web.views.image_osint.urls")),
    path("email-osint/", include("app.web.views.email_osint.urls")),
    path("username-osint/", include("app.web.views.username_osint.urls")),
    path("nmap-scan/", include("app.web.views.nmap_scan.urls")),
    path("scan-job/", include("app.web.views.scan_job.urls")),
    path("analiz/", include("app.web.views.analiz.urls")),
]
