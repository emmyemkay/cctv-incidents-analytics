from django.urls import path

from . import views

app_name = "platform_core"
urlpatterns = [
    path("live/", views.live, name="live"),
    path("ready/", views.ready, name="ready"),
]
