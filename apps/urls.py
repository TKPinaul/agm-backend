from django.urls import path, include

urlpatterns = [
    # Gestion des utilisateurs
    path('users-controls/', include('apps.users.urls')),
    
    
    # path('core/', include('apps.core.urls')),
]
