"""
URL configuration for c2m_gym project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler400, handler403, handler404, handler500
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from gymApp.views import stripe_webhook, set_language


# Custom error handlers
handler400 = 'gymApp.views.custom_bad_request_view'
handler403 = 'gymApp.views.custom_permission_denied_view'
handler404 = 'gymApp.views.custom_page_not_found_view'
handler500 = 'gymApp.views.custom_server_error_view'

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('set_language/', set_language, name='set_language'),
    path('gym/webhook/', stripe_webhook, name='stripe_webhook')

]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('gym/', include('gymApp.urls')),
    path('', include('gym_info.urls')),
    path('classes/', include('class_schedule.urls')),
    path('products/', include('products.urls')),
    path('documents/', include('documentation.urls')),
)

# This is for serving media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)