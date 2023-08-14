from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from chat.forms import RoomForm
from chat.models import Room, Message


def index(request: HttpRequest) -> HttpResponse:
    room_list = Room.objects.all().filter(is_public=True)
    return render(request, "chat/index.html", {"room_list": room_list})


@login_required
def room_chat(request: HttpRequest, room_pk: str) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_pk)
    return render(request, "chat/room_chat.html", {"room": room})


@login_required
def room_new(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            created_room: Room = form.save(commit=False)
            created_room.owner = request.user
            created_room.save()
            return redirect("chat:room_chat", created_room.pk)
    else:
        form = RoomForm()
    return render(request, "chat/room_form.html", {"form": form})


@login_required
def room_delete(request: HttpRequest, room_pk: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_pk)
    if room.owner != request.user:
        messages.error(request, "채팅방 소유자가 아닙니다.")
        return redirect("chat:index")
    if request.method == "POST":
        room.delete()
        messages.success(request, "채팅방을 삭제하였습니다.")
        return redirect("chat:index")
    return render(request, "chat/room_confirm_delete.html", {"room": room})


@login_required
def room_users(request, room_pk):
    room = get_object_or_404(Room, pk=room_pk)
    if not room.is_joined_user(request.user):
        return HttpResponse("Unauthorized user", status=401)
    username_list = room.get_online_usernames()
    return JsonResponse({"username_list": username_list})


@login_required
def lobby_users(request):
    room = get_object_or_404(Room, pk=2)
    if not room.is_joined_user(request.user):
        return HttpResponse("Unauthorized user", status=401)
    username_list = room.get_online_usernames()
    return JsonResponse({"username_list": username_list})


@login_required
def room_past_message(request, room_pk):
    room = get_object_or_404(Room, pk=room_pk)
    last_five_message = Message.objects.filter(room=room)[:5][::-1]
    message = []
    for i, obj in enumerate(last_five_message):
        message.append(
            {
                "sender": obj.sender.username,
                "message": obj.content,
                "time": timezone.datetime.strftime(obj.created_at, "%y/%m/%d %H:%M:%S"),
                "img": obj.sender.avatar.url,
            }
        )
    return JsonResponse({"message": message})
