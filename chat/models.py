from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import QuerySet
from django.db.models.signals import post_delete

from mysite.json_extended import ExtendedJSONEncoder, ExtendedJSONDecoder


class OnlineUserMixin(models.Model):
    class Meta:
        abstract = True

    online_user_set = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="RoomMember",
        blank=True,
        related_name="joined_room_set",
    )

    def get_online_users(self) -> QuerySet:
        return self.online_user_set.all()

    def get_online_usernames(self) -> list[str]:
        qs = self.get_online_users().values_list("username", flat=True)
        return list(qs)

    def is_joined_user(self, user) -> bool:
        return self.get_online_users().filter(pk=user.pk).exists()

    def user_join(self, channel_name, user) -> bool:
        try:
            room_member = RoomMember.objects.get(room=self, user=user)
        except RoomMember.DoesNotExist:
            room_member = RoomMember(room=self, user=user)
        is_new_join = len(room_member.channel_names) == 0
        room_member.channel_names.add(channel_name)

        if room_member.pk is None:
            room_member.save()
        else:
            room_member.save(update_fields=["channel_names"])
        return is_new_join

    def user_leave(self, channel_name, user) -> bool:
        try:
            room_member = RoomMember.objects.get(room=self, user=user)
        except RoomMember.DoesNotExist:
            return True
        room_member.channel_names.remove(channel_name)
        if not room_member.channel_names:
            room_member.delete()
            return True
        else:
            room_member.save(update_fields=["channel_names"])
            return False

    def delete_room(self):
        try:
            room_member = RoomMember.objects.get(room=self)
        except RoomMember.DoesNotExist:
            self.delete()


class Room(OnlineUserMixin, models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_room_set",
    )
    name = models.CharField(max_length=100)
    is_public = models.BooleanField(default=True, verbose_name="공개여부")

    @property
    def chat_group_name(self) -> str:
        return self.make_chat_group_name(room=self)

    @classmethod
    def make_chat_group_name(cls, room=None, room_pk=None) -> str:
        return "chat-%s" % (room_pk or room.pk)

    class Meta:
        ordering = ["-pk"]


def room__on_post_delete(instance: Room, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        instance.chat_group_name, {"type": "chat.room.deleted"}
    )


post_delete.connect(
    room__on_post_delete, sender=Room, dispatch_uid="room__on_post_delete"
)


class RoomMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey("Room", on_delete=models.CASCADE)
    channel_names = models.JSONField(
        default=set, encoder=ExtendedJSONEncoder, decoder=ExtendedJSONDecoder
    )


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content

    class Meta:
        ordering = ["-created_at"]


# class ChannelNames(models.Model):
#     names = models.CharField(max_length=100)


class LobbyMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    channel_names = models.JSONField(
        default=set, encoder=ExtendedJSONEncoder, decoder=ExtendedJSONDecoder
    )

    @classmethod
    def get_count(cls):
        return cls.objects.all().count()

    # channel_names = models.JSONField(
    #     default=set, encoder=ExtendedJSONEncoder, decoder=ExtendedJSONDecoder
    # )
    #
    # @classmethod
    # def user_join(cls, channel_names):
    #     lobby = cls.objects.first()
    #     print(lobby)
    #     if lobby is None:
    #         lobby = LobbyMember(channel_names=channel_names)
    #     else:
    #         lobby.channel_names.add(channel_names)
    #     print(lobby)
    #     lobby.save(update_fields=["channel_names"])
    #
    # @classmethod
    # def user_leave(cls, channel_names):
    #     lobby = cls.objects.first()
    #     lobby.channel_names.remove(channel_names)
    #     lobby.save(update_fields=["channel_names"])
    #
    # @classmethod
    # def get_channel_count(cls):
    #     return len(cls.channel_names["values"])
