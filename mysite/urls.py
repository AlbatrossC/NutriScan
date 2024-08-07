from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),            # Admin interface
    path('', include('image_processor.urls')),  # Include the URLs from the image_processor app
]
