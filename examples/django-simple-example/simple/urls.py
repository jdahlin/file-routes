"""simple URL Configuration

The `urlpatterns` list routes URLs to routes. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function routes
    1. Add an import:  from my_app import routes
    2. Add a URL to urlpatterns:  path('', routes.home, name='home')
Class-based routes
    1. Add an import:  from other_app.routes import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
