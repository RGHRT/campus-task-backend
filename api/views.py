import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers

from .models import Task
from .response import success_response, error_response
from .serializers import task_to_dict, user_to_dict

def hello(request):
    return success_response(
        data={
            "message": "我的第一个 Python 后端接口"
        },
        message="请求成功"
    )


def task_list(request):
    if request.method != "GET":
        return error_response(
            message="只允许使用 GET 请求",
            code=405
        )

    status = request.GET.get("status")
    keyword = request.GET.get("keyword")

    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 5)

    try:
        page = int(page)
        page_size = int(page_size)
    except ValueError:
        return error_response(
            message="page 和 page_size 必须是数字",
            code=400
        )

    if page <= 0:
        return error_response(
            message="page 必须大于 0",
            code=400
        )

    if page_size <= 0:
        return error_response(
            message="page_size 必须大于 0",
            code=400
        )

    tasks = Task.objects.all().order_by("-created_at")

    if status:
        tasks = tasks.filter(status=status)

    if keyword:
        tasks = tasks.filter(
            Q(title__contains=keyword) | Q(description__contains=keyword)
        )

    total = tasks.count()

    start = (page - 1) * page_size
    end = start + page_size

    tasks = tasks[start:end]

    task_data = [task_to_dict(task) for task in tasks]

    data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": task_data
    }

    return success_response(
        data=data,
        message="获取任务列表成功"
    )
@extend_schema(
    summary="发布任务",
    description="登录用户发布一个新的校园互助任务。",
    tags=["任务"],
    request=inline_serializer(
        name="CreateTaskRequest",
        fields={
            "title": serializers.CharField(
                max_length=100,
                help_text="任务标题",
            ),
            "description": serializers.CharField(
                help_text="任务详细描述",
            ),
            "reward": serializers.DecimalField(
                max_digits=8,
                decimal_places=2,
                required=False,
                default=0,
                help_text="任务报酬，最多保留两位小数",
            ),
        },
    ),
    responses={
        200: OpenApiResponse(description="任务创建成功"),
        400: OpenApiResponse(description="请求参数错误"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
    },
)
@api_view(["POST"])
def create_task(request):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录后再发布任务",
            code=401
        )

    try:
        data = request.data
    except ParseError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400
        )

    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    reward_value = data.get("reward", 0)

    if not title:
        return error_response(
            message="任务标题不能为空",
            code=400
        )

    if len(title) > 100:
        return error_response(
            message="任务标题不能超过 100 个字符",
            code=400
        )

    if not description:
        return error_response(
            message="任务描述不能为空",
            code=400
        )

    try:
        reward = Decimal(str(reward_value))
    except (InvalidOperation, TypeError, ValueError):
        return error_response(
            message="任务报酬必须是数字",
            code=400
        )

    if reward < 0:
        return error_response(
            message="任务报酬不能小于 0",
            code=400
        )

    if reward > Decimal("999999.99"):
        return error_response(
            message="任务报酬不能超过 999999.99",
            code=400
        )

    if reward.quantize(Decimal("0.01")) != reward:
        return error_response(
            message="任务报酬最多保留两位小数",
            code=400
        )

    task = Task.objects.create(
        publisher=request.user,
        title=title,
        description=description,
        reward=reward,
        status=Task.Status.PENDING
    )

    return success_response(
        data=task_to_dict(task),
        message="任务创建成功"
    )
def task_detail(request, task_id):
    if request.method != "GET":
        return error_response(
            message="只允许使用 GET 请求",
            code=405
        )

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404
        )

    task_data = task_to_dict(task)

    return success_response(
        data=task_data,
        message="获取任务详情成功"
    )

@csrf_exempt
def update_task(request, task_id):
    if request.method != "PUT":
        return error_response(
            message="只允许使用 PUT 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404
        )

    if task.publisher_id != request.user.id:
        return error_response(
            message="只能修改自己发布的任务",
            code=403
        )

    # 任务被接取后，不能再修改标题、描述和报酬
    if task.status != Task.Status.PENDING or task.receiver_id is not None:
        return error_response(
            message="任务已被接取或已结束，不能修改",
            code=409
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400
        )

    title = data.get("title")
    description = data.get("description")
    reward = data.get("reward")

    if title is not None:
        title = title.strip()

        if not title:
            return error_response(
                message="任务标题不能为空",
                code=400
            )

        task.title = title

    if description is not None:
        description = description.strip()

        if not description:
            return error_response(
                message="任务描述不能为空",
                code=400
            )

        task.description = description

    if reward is not None:
        try:
            reward = float(reward)
        except (TypeError, ValueError):
            return error_response(
                message="任务报酬必须是数字",
                code=400
            )

        if reward < 0:
            return error_response(
                message="任务报酬不能小于 0",
                code=400
            )

        task.reward = reward

    task.save()

    return success_response(
        data=task_to_dict(task),
        message="任务修改成功"
    )
@csrf_exempt
def delete_task(request, task_id):
    if request.method != "DELETE":
        return error_response(
            message="只允许使用 DELETE 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404
        )

    if task.publisher_id != request.user.id:
        return error_response(
            message="只能删除自己发布的任务",
            code=403
        )

    if task.receiver_id is not None:
        return error_response(
            message="已有接单者的任务不能删除",
            code=409
        )

    if task.status != Task.Status.CANCELLED:
        return error_response(
            message="请先取消任务，再执行删除",
            code=409
        )

    task.delete()

    return success_response(
        data=None,
        message="任务删除成功"
    )
@csrf_exempt
def register_user(request):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400
        )
    if "status" in data:
        return error_response(
            message="不能通过普通修改接口修改任务状态",
            code=400
        )
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    if not username:
        return error_response(
            message="用户名不能为空",
            code=400
        )

    if not password:
        return error_response(
            message="密码不能为空",
            code=400
        )

    if len(password) < 6:
        return error_response(
            message="密码长度不能少于 6 位",
            code=400
        )

    if User.objects.filter(username=username).exists():
        return error_response(
            message="用户名已存在",
            code=400
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )

    return success_response(
        data=user_to_dict(user),
        message="用户注册成功"
    )
@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400
        )

    username = data.get("username")
    password = data.get("password")

    if not username:
        return error_response(
            message="用户名不能为空",
            code=400
        )

    if not password:
        return error_response(
            message="密码不能为空",
            code=400
        )

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:
        return error_response(
            message="用户名或密码错误",
            code=400
        )

    login(request, user)

    return success_response(
        data=user_to_dict(user),
        message="用户登录成功"
    )
def current_user(request):
    if request.method != "GET":
        return error_response(
            message="只允许使用 GET 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="用户未登录",
            code=401
        )

    return success_response(
        data=user_to_dict(request.user),
        message="获取当前用户成功"
    )

@extend_schema(
    summary="获取当前JWT用户",
    description="携带有效的 Access Token，获取当前登录用户的信息。",
    tags=["用户"],
    responses={
        200: OpenApiResponse(description="获取当前用户成功"),
        401: OpenApiResponse(description="未登录、Token无效或Token已过期"),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def jwt_me(request):
    return success_response(
        data=user_to_dict(request.user),
        message="获取当前用户成功",
    )

@csrf_exempt
def logout_user(request):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="用户未登录",
            code=401
        )

    logout(request)

    return success_response(
        data=None,
        message="退出登录成功"
    )
def my_task_list(request):
    if request.method != "GET":
        return error_response(
            message="只允许使用 GET 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    tasks = Task.objects.filter(
        publisher=request.user
    ).order_by("-created_at")

    task_data = [
        task_to_dict(task)
        for task in tasks
    ]

    return success_response(
        data=task_data,
        message="获取我发布的任务成功"
    )
@csrf_exempt
def accept_task(request, task_id):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404
            )

        if task.publisher_id == request.user.id:
            return error_response(
                message="不能接取自己发布的任务",
                code=403
            )

        if task.receiver_id is not None:
            return error_response(
                message="该任务已经被接取",
                code=409
            )

        if task.status != Task.Status.PENDING:
            return error_response(
                message="当前任务状态不允许接取",
                code=409
            )

        task.receiver = request.user
        task.status = Task.Status.IN_PROGRESS

        task.save(
            update_fields=[
                "receiver",
                "status"
            ]
        )

    return success_response(
        data=task_to_dict(task),
        message="任务接取成功"
    )
def my_received_task_list(request):
    if request.method != "GET":
        return error_response(
            message="只允许使用 GET 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    tasks = Task.objects.filter(
        receiver=request.user
    ).order_by("-created_at")

    task_data = [
        task_to_dict(task)
        for task in tasks
    ]

    return success_response(
        data=task_data,
        message="获取我接取的任务成功"
    )
@csrf_exempt
def complete_task(request, task_id):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404
            )

        if task.receiver_id != request.user.id:
            return error_response(
                message="只有接单者才能提交任务完成",
                code=403
            )

        if task.status != Task.Status.IN_PROGRESS:
            return error_response(
                message="只有进行中的任务才能提交完成",
                code=409
            )

        task.status = Task.Status.WAITING_CONFIRM

        task.save(
            update_fields=["status"]
        )

    return success_response(
        data=task_to_dict(task),
        message="任务已提交完成，等待发布者确认"
    )
@csrf_exempt
def confirm_task(request, task_id):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404
            )

        if task.publisher_id != request.user.id:
            return error_response(
                message="只有任务发布者才能确认完成",
                code=403
            )

        if task.status != Task.Status.WAITING_CONFIRM:
            return error_response(
                message="只有待确认的任务才能确认完成",
                code=409
            )

        task.status = Task.Status.COMPLETED

        task.save(
            update_fields=["status"]
        )

    return success_response(
        data=task_to_dict(task),
        message="任务已确认完成"
    )
@csrf_exempt
def cancel_task(request, task_id):
    if request.method != "POST":
        return error_response(
            message="只允许使用 POST 请求",
            code=405
        )

    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404
            )

        if task.publisher_id != request.user.id:
            return error_response(
                message="只有任务发布者才能取消任务",
                code=403
            )

        if task.receiver_id is not None:
            return error_response(
                message="任务已经被接取，不能取消",
                code=409
            )

        if task.status != Task.Status.PENDING:
            return error_response(
                message="当前任务状态不能取消",
                code=409
            )

        task.status = Task.Status.CANCELLED

        task.save(
            update_fields=["status"]
        )

    return success_response(
        data=task_to_dict(task),
        message="任务取消成功"
    )