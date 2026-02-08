from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('src.Presentation.urls.auth_urls')),
    path('api/', include('src.Presentation.urls.admin_urls')),
]

