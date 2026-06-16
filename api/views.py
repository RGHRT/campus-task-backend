from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)

from .models import Task
from .response import error_response, success_response
from .serializers import task_to_dict, user_to_dict


CREATE_TASK_REQUEST = inline_serializer(
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
)

UPDATE_TASK_REQUEST = inline_serializer(
    name="UpdateTaskRequest",
    fields={
        "title": serializers.CharField(
            max_length=100,
            required=False,
            help_text="新的任务标题",
        ),
        "description": serializers.CharField(
            required=False,
            help_text="新的任务描述",
        ),
        "reward": serializers.DecimalField(
            max_digits=8,
            decimal_places=2,
            required=False,
            help_text="新的任务报酬",
        ),
    },
)

REGISTER_REQUEST = inline_serializer(
    name="RegisterRequest",
    fields={
        "username": serializers.CharField(help_text="用户名"),
        "password": serializers.CharField(
            min_length=6,
            write_only=True,
            help_text="密码，至少6位",
        ),
        "email": serializers.EmailField(
            required=False,
            allow_blank=True,
            help_text="邮箱",
        ),
    },
)

LOGIN_REQUEST = inline_serializer(
    name="SessionLoginRequest",
    fields={
        "username": serializers.CharField(help_text="用户名"),
        "password": serializers.CharField(
            write_only=True,
            help_text="密码",
        ),
    },
)


def _parse_reward(value):
    try:
        reward = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None, error_response(
            message="任务报酬必须是数字",
            code=400,
        )

    if reward < 0:
        return None, error_response(
            message="任务报酬不能小于 0",
            code=400,
        )

    if reward > Decimal("999999.99"):
        return None, error_response(
            message="任务报酬不能超过 999999.99",
            code=400,
        )

    if reward.quantize(Decimal("0.01")) != reward:
        return None, error_response(
            message="任务报酬最多保留两位小数",
            code=400,
        )

    return reward, None


@extend_schema(
    summary="接口连通性测试",
    tags=["系统"],
    responses={200: OpenApiResponse(description="请求成功")},
)
@api_view(["GET"])
def hello(request):
    return success_response(
        data={"message": "我的第一个 Python 后端接口"},
        message="请求成功",
    )


@extend_schema(
    operation_id="tasks_list",
    summary="获取任务列表",
    description="支持按状态筛选、关键词搜索和分页查询。",
    tags=["任务"],
    parameters=[
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="任务状态，例如：未完成、进行中、待确认、已完成、已取消",
        ),
        OpenApiParameter(
            name="keyword",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="在任务标题和描述中搜索关键词",
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="页码，默认1",
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="每页数量，默认5",
        ),
    ],
    responses={
        200: OpenApiResponse(description="获取任务列表成功"),
        400: OpenApiResponse(description="分页参数错误"),
    },
)
@api_view(["GET"])
def task_list(request):
    status = request.query_params.get("status")
    keyword = request.query_params.get("keyword")
    page = request.query_params.get("page", 1)
    page_size = request.query_params.get("page_size", 5)

    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        return error_response(
            message="page 和 page_size 必须是数字",
            code=400,
        )

    if page <= 0:
        return error_response(
            message="page 必须大于 0",
            code=400,
        )

    if page_size <= 0:
        return error_response(
            message="page_size 必须大于 0",
            code=400,
        )

    tasks = Task.objects.select_related(
        "publisher",
        "receiver",
    ).all().order_by("-created_at")

    if status:
        tasks = tasks.filter(status=status)

    if keyword:
        tasks = tasks.filter(
            Q(title__contains=keyword)
            | Q(description__contains=keyword)
        )

    total = tasks.count()
    start = (page - 1) * page_size
    end = start + page_size
    task_data = [task_to_dict(task) for task in tasks[start:end]]

    return success_response(
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "list": task_data,
        },
        message="获取任务列表成功",
    )


@extend_schema(
    summary="发布任务",
    description="登录用户发布一个新的校园互助任务。",
    tags=["任务"],
    request=CREATE_TASK_REQUEST,
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
            code=401,
        )

    try:
        data = request.data
    except ParseError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400,
        )

    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    reward_value = data.get("reward", 0)

    if not title:
        return error_response(
            message="任务标题不能为空",
            code=400,
        )

    if len(title) > 100:
        return error_response(
            message="任务标题不能超过 100 个字符",
            code=400,
        )

    if not description:
        return error_response(
            message="任务描述不能为空",
            code=400,
        )

    reward, reward_error = _parse_reward(reward_value)
    if reward_error:
        return reward_error

    task = Task.objects.create(
        publisher=request.user,
        title=title,
        description=description,
        reward=reward,
        status=Task.Status.PENDING,
    )

    return success_response(
        data=task_to_dict(task),
        message="任务创建成功",
    )


@extend_schema(
    operation_id="tasks_retrieve",
    summary="获取任务详情",
    tags=["任务"],
    responses={
        200: OpenApiResponse(description="获取任务详情成功"),
        404: OpenApiResponse(description="任务不存在"),
    },
)
@api_view(["GET"])
def task_detail(request, task_id):
    try:
        task = Task.objects.select_related(
            "publisher",
            "receiver",
        ).get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404,
        )

    return success_response(
        data=task_to_dict(task),
        message="获取任务详情成功",
    )


@extend_schema(
    summary="修改任务",
    description="只有发布者可以修改尚未被接取的未完成任务。",
    tags=["任务"],
    request=UPDATE_TASK_REQUEST,
    responses={
        200: OpenApiResponse(description="任务修改成功"),
        400: OpenApiResponse(description="请求参数错误"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="只能修改自己发布的任务"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="当前任务不能修改"),
    },
)
@api_view(["PUT"])
def update_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404,
        )

    if task.publisher_id != request.user.id:
        return error_response(
            message="只能修改自己发布的任务",
            code=403,
        )

    if task.status != Task.Status.PENDING or task.receiver_id is not None:
        return error_response(
            message="任务已被接取或已结束，不能修改",
            code=409,
        )

    try:
        data = request.data
    except ParseError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400,
        )

    if "status" in data:
        return error_response(
            message="不能通过普通修改接口修改任务状态",
            code=400,
        )

    title = data.get("title")
    description = data.get("description")
    reward_value = data.get("reward")

    if title is not None:
        title = str(title).strip()
        if not title:
            return error_response(
                message="任务标题不能为空",
                code=400,
            )
        if len(title) > 100:
            return error_response(
                message="任务标题不能超过 100 个字符",
                code=400,
            )
        task.title = title

    if description is not None:
        description = str(description).strip()
        if not description:
            return error_response(
                message="任务描述不能为空",
                code=400,
            )
        task.description = description

    if reward_value is not None:
        reward, reward_error = _parse_reward(reward_value)
        if reward_error:
            return reward_error
        task.reward = reward

    task.save()

    return success_response(
        data=task_to_dict(task),
        message="任务修改成功",
    )


@extend_schema(
    summary="删除任务",
    description="只有发布者可以删除已经取消且没有接单者的任务。",
    tags=["任务"],
    request=None,
    responses={
        200: OpenApiResponse(description="任务删除成功"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="只能删除自己发布的任务"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="当前任务不能删除"),
    },
)
@api_view(["DELETE"])
def delete_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return error_response(
            message="任务不存在",
            code=404,
        )

    if task.publisher_id != request.user.id:
        return error_response(
            message="只能删除自己发布的任务",
            code=403,
        )

    if task.receiver_id is not None:
        return error_response(
            message="已有接单者的任务不能删除",
            code=409,
        )

    if task.status != Task.Status.CANCELLED:
        return error_response(
            message="请先取消任务，再执行删除",
            code=409,
        )

    task.delete()

    return success_response(
        data=None,
        message="任务删除成功",
    )


@extend_schema(
    summary="用户注册",
    tags=["用户"],
    request=REGISTER_REQUEST,
    responses={
        200: OpenApiResponse(description="用户注册成功"),
        400: OpenApiResponse(description="注册参数错误"),
    },
)
@api_view(["POST"])
def register_user(request):
    try:
        data = request.data
    except ParseError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400,
        )

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    email = str(data.get("email", "")).strip()

    if not username:
        return error_response(
            message="用户名不能为空",
            code=400,
        )

    if not password:
        return error_response(
            message="密码不能为空",
            code=400,
        )

    if len(password) < 6:
        return error_response(
            message="密码长度不能少于 6 位",
            code=400,
        )

    if User.objects.filter(username=username).exists():
        return error_response(
            message="用户名已存在",
            code=400,
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
    )

    return success_response(
        data=user_to_dict(user),
        message="用户注册成功",
    )


@extend_schema(
    summary="Session登录",
    description="保留给旧客户端和Django Session测试使用；前后端分离建议使用JWT登录接口。",
    tags=["用户"],
    request=LOGIN_REQUEST,
    responses={
        200: OpenApiResponse(description="用户登录成功"),
        400: OpenApiResponse(description="用户名或密码错误"),
    },
)
@api_view(["POST"])
def login_user(request):
    try:
        data = request.data
    except ParseError:
        return error_response(
            message="请求体不是合法的 JSON",
            code=400,
        )

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username:
        return error_response(
            message="用户名不能为空",
            code=400,
        )

    if not password:
        return error_response(
            message="密码不能为空",
            code=400,
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return error_response(
            message="用户名或密码错误",
            code=400,
        )

    login(request, user)

    return success_response(
        data=user_to_dict(user),
        message="用户登录成功",
    )


@extend_schema(
    summary="获取当前用户",
    description="支持JWT或Session认证。",
    tags=["用户"],
    responses={
        200: OpenApiResponse(description="获取当前用户成功"),
        401: OpenApiResponse(description="用户未登录"),
    },
)
@api_view(["GET"])
def current_user(request):
    if not request.user.is_authenticated:
        return error_response(
            message="用户未登录",
            code=401,
        )

    return success_response(
        data=user_to_dict(request.user),
        message="获取当前用户成功",
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


@extend_schema(
    summary="退出Session登录",
    description="清除当前Session。JWT令牌不会因此失效。",
    tags=["用户"],
    request=None,
    responses={
        200: OpenApiResponse(description="退出登录成功"),
        401: OpenApiResponse(description="用户未登录"),
    },
)
@api_view(["POST"])
def logout_user(request):
    if not request.user.is_authenticated:
        return error_response(
            message="用户未登录",
            code=401,
        )

    logout(request)

    return success_response(
        data=None,
        message="退出登录成功",
    )


@extend_schema(
    summary="获取我发布的任务",
    tags=["任务"],
    responses={
        200: OpenApiResponse(description="获取我发布的任务成功"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
    },
)
@api_view(["GET"])
def my_task_list(request):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    tasks = Task.objects.select_related(
        "publisher",
        "receiver",
    ).filter(
        publisher=request.user,
    ).order_by("-created_at")

    return success_response(
        data=[task_to_dict(task) for task in tasks],
        message="获取我发布的任务成功",
    )


@extend_schema(
    summary="接取任务",
    description="登录用户接取一个尚未被其他用户接取的任务。",
    tags=["任务"],
    request=None,
    responses={
        200: OpenApiResponse(description="任务接取成功"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="不能接取自己发布的任务"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="任务已被接取或状态不允许接取"),
    },
)
@api_view(["POST"])
def accept_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404,
            )

        if task.publisher_id == request.user.id:
            return error_response(
                message="不能接取自己发布的任务",
                code=403,
            )

        if task.receiver_id is not None:
            return error_response(
                message="该任务已经被接取",
                code=409,
            )

        if task.status != Task.Status.PENDING:
            return error_response(
                message="当前任务状态不允许接取",
                code=409,
            )

        task.receiver = request.user
        task.status = Task.Status.IN_PROGRESS
        task.save(update_fields=["receiver", "status"])

    return success_response(
        data=task_to_dict(task),
        message="任务接取成功",
    )


@extend_schema(
    summary="获取我接取的任务",
    tags=["任务"],
    responses={
        200: OpenApiResponse(description="获取我接取的任务成功"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
    },
)
@api_view(["GET"])
def my_received_task_list(request):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    tasks = Task.objects.select_related(
        "publisher",
        "receiver",
    ).filter(
        receiver=request.user,
    ).order_by("-created_at")

    return success_response(
        data=[task_to_dict(task) for task in tasks],
        message="获取我接取的任务成功",
    )


@extend_schema(
    summary="提交任务完成",
    description="任务接单者提交任务完成，提交后等待发布者确认。",
    tags=["任务"],
    request=None,
    responses={
        200: OpenApiResponse(description="任务已提交完成，等待发布者确认"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="当前用户不是该任务的接单者"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="任务不是进行中状态"),
    },
)
@api_view(["POST"])
def complete_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404,
            )

        if task.receiver_id != request.user.id:
            return error_response(
                message="只有接单者才能提交任务完成",
                code=403,
            )

        if task.status != Task.Status.IN_PROGRESS:
            return error_response(
                message="只有进行中的任务才能提交完成",
                code=409,
            )

        task.status = Task.Status.WAITING_CONFIRM
        task.save(update_fields=["status"])

    return success_response(
        data=task_to_dict(task),
        message="任务已提交完成，等待发布者确认",
    )


@extend_schema(
    summary="确认任务完成",
    description="任务发布者确认接单者已经完成任务。",
    tags=["任务"],
    request=None,
    responses={
        200: OpenApiResponse(description="任务已确认完成"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="当前用户不是任务发布者"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="任务不是待确认状态"),
    },
)
@api_view(["POST"])
def confirm_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404,
            )

        if task.publisher_id != request.user.id:
            return error_response(
                message="只有任务发布者才能确认完成",
                code=403,
            )

        if task.status != Task.Status.WAITING_CONFIRM:
            return error_response(
                message="只有待确认的任务才能确认完成",
                code=409,
            )

        task.status = Task.Status.COMPLETED
        task.save(update_fields=["status"])

    return success_response(
        data=task_to_dict(task),
        message="任务已确认完成",
    )


@extend_schema(
    summary="取消任务",
    description="任务发布者取消尚未被接取的未完成任务。",
    tags=["任务"],
    request=None,
    responses={
        200: OpenApiResponse(description="任务取消成功"),
        401: OpenApiResponse(description="用户未登录或Token无效"),
        403: OpenApiResponse(description="当前用户不是任务发布者"),
        404: OpenApiResponse(description="任务不存在"),
        409: OpenApiResponse(description="任务已被接取或状态不允许取消"),
    },
)
@api_view(["POST"])
def cancel_task(request, task_id):
    if not request.user.is_authenticated:
        return error_response(
            message="请先登录",
            code=401,
        )

    with transaction.atomic():
        try:
            task = Task.objects.select_for_update().get(id=task_id)
        except Task.DoesNotExist:
            return error_response(
                message="任务不存在",
                code=404,
            )

        if task.publisher_id != request.user.id:
            return error_response(
                message="只有任务发布者才能取消任务",
                code=403,
            )

        if task.receiver_id is not None:
            return error_response(
                message="任务已经被接取，不能取消",
                code=409,
            )

        if task.status != Task.Status.PENDING:
            return error_response(
                message="当前任务状态不能取消",
                code=409,
            )

        task.status = Task.Status.CANCELLED
        task.save(update_fields=["status"])

    return success_response(
        data=task_to_dict(task),
        message="任务取消成功",
    )
