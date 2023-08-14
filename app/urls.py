from django.urls import path
from . import views

urlpatterns = [
    path("echo/", views.echo_page, name="echo_page"),
    path("liveblog/", views.liveblog_index, name="liveblog_index"),
    path("liveblog/posts/<int:post_id>/", views.post_partial, name="post_partial"),
]
