from django.urls import path
from chat import views

app_name = "chat"
urlpatterns = [
    path("", views.index, name="index"),
    path("<str:room_pk>/chat/", views.room_chat, name="room_chat"),
    path("new/", views.room_new, name="room_new"),
    path("<int:room_pk>/delete/", views.room_delete, name="room_delete"),
    path("<int:room_pk>/users/", views.room_users, name="room_users"),
    path(
        "<int:room_pk>/past/message/", views.room_past_message, name="room_past_message"
    ),
    path("lobby/users/", views.lobby_users, name="lobby_users"),
]
