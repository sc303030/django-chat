from django.shortcuts import get_object_or_404
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from chat.models import Room, LobbyMember, Message


class ChatConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = ""
        self.room = None
        self.room_pk = None

    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            self.close()
        else:
            self.room_pk = self.scope["url_route"]["kwargs"]["room_pk"]
            try:
                self.room = Room.objects.get(pk=self.room_pk)
            except Room.DoesNotExist:
                self.close()
            else:
                self.group_name = self.room.chat_group_name
                is_new_join = self.room.user_join(self.channel_name, user)
                if is_new_join:
                    last_five_message = Message.objects.filter(room=self.room)[:5][::-1]
                    message = []
                    for i, obj in enumerate(last_five_message):
                        message.append(
                            {
                                "sender": obj.sender.username,
                                "message": obj.content,
                                "time": timezone.datetime.strftime(
                                    obj.created_at, "%y/%m/%d %H:%M:%S"
                                ),
                                "img": obj.sender.avatar.url,
                            }
                        )
                    async_to_sync(self.channel_layer.group_send)(
                        self.group_name,
                        {
                            "type": "chat.user.join",
                            "username": user.username,
                            "message": message,
                        },
                    )
                async_to_sync(self.channel_layer.group_add)(
                    self.group_name, self.channel_name
                )
                self.accept()

    def disconnect(self, code):
        if self.group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )
        user = self.scope["user"]
        if self.room is not None:
            is_last_leave = self.room.user_leave(self.channel_name, user)
            if is_last_leave:
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {"type": "chat.user.leave", "username": user.username},
                )
                # self.room.delete_room()

    def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        _type = content["type"]

        if _type == "chat.message":
            sender = user.username
            message = Message.objects.create(
                room=self.room, sender=user, content=content["message"]
            )
            time_str = timezone.datetime.strftime(
                message.created_at, "%y/%m/%d %H:%M:%S"
            )
            img = user.avatar.url
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "chat.message",
                    "pk": message.pk,
                    "message": message.content,
                    "sender": sender,
                    "time": time_str,
                    "img": img,
                },
            )
        elif _type == "chat.message.modify":
            message_pk = content["message_pk"]
            message = get_object_or_404(Message, pk=message_pk, room=self.room)
            message.content = content["message"]
            message.save(update_fields=["content", "updated_at"])
            time_str = timezone.datetime.strftime(
                message.updated_at, "%y/%m/%d %H:%M:%S"
            )
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "chat.message.modify.success",
                    "pk": message.pk,
                    "message": message.content,
                    "time": time_str,
                },
            )
        elif _type == "chat.message.delete":
            message_pk = content["message_pk"]
            message = get_object_or_404(Message, pk=message_pk, room=self.room)
            message.delete()
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "chat.message.delete",
                    "pk": message_pk,
                },
            )
        else:
            print(f"Invalid message type : {_type}")

    def chat_message(self, message_dict):
        self.send_json(
            {
                "type": "chat.message",
                "pk": message_dict["pk"],
                "message": message_dict["message"],
                "sender": message_dict["sender"],
                "time": message_dict["time"],
                "img": message_dict["img"],
            }
        )

    def chat_room_deleted(self, message_dict):
        custom_code = 4000
        self.close(code=custom_code)

    def chat_user_join(self, message_dict):
        self.send_json(
            {
                "type": "chat.user.join",
                "username": message_dict["username"],
                "message": message_dict["message"],
            }
        )

    def chat_user_leave(self, message_dict):
        self.send_json(
            {"type": "chat.user.leave", "username": message_dict["username"]}
        )

    def chat_message_modify_fail(self, message_dict):
        self.send_json(
            {"type": "chat.message.modify.fail", "message": message_dict["message"]}
        )

    def chat_message_modify_success(self, message_dict):
        self.send_json(
            {
                "type": "chat.message.modify.success",
                "pk": message_dict["pk"],
                "message": message_dict["message"],
                "time": message_dict["time"],
            }
        )

    def chat_message_delete(self, message_dict):
        self.send_json(
            {
                "type": "chat.message.delete",
                "pk": message_dict["pk"],
            }
        )


class LobbyConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = ""
        self.room = None
        self.room_pk = 2

    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            self.close()
        else:
            try:
                self.room = Room.objects.get(pk=self.room_pk)
            except Room.DoesNotExist:
                self.close()
            else:
                self.group_name = self.room.chat_group_name
                is_new_join = self.room.user_join(self.channel_name, user)
                if is_new_join:
                    async_to_sync(self.channel_layer.group_send)(
                        self.group_name,
                        {"type": "chat.user.join", "username": user.username},
                    )
                async_to_sync(self.channel_layer.group_add)(
                    self.group_name, self.channel_name
                )
                self.accept()

    def disconnect(self, code):
        if self.group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )
        user = self.scope["user"]
        if self.room is not None:
            is_last_leave = self.room.user_leave(self.channel_name, user)
            if is_last_leave:
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {"type": "chat.user.leave", "username": user.username},
                )
                # self.room.delete_room()

    def chat_room_deleted(self, message_dict):
        custom_code = 4000
        self.close(code=custom_code)

    def chat_user_join(self, message_dict):
        self.send_json({"type": "chat.user.join", "username": message_dict["username"]})

    def chat_user_leave(self, message_dict):
        self.send_json(
            {"type": "chat.user.leave", "username": message_dict["username"]}
        )
