from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    accept_task,
    cancel_task,
    complete_task,
    confirm_task,
    create_task,
    current_user,
    delete_task,
    hello,
    jwt_me,
    login_user,
    logout_user,
    my_received_task_list,
    my_task_list,
    register_user,
    task_detail,
    task_list,
    update_task,
)

urlpatterns = [
    path("hello/", hello),
    path("tasks/", task_list),
    path("tasks/create/", create_task),
    path("tasks/mine/", my_task_list),
    path("tasks/received/", my_received_task_list),
    path("tasks/<int:task_id>/accept/", accept_task),
    path("tasks/<int:task_id>/complete/", complete_task),
    path("tasks/<int:task_id>/confirm/", confirm_task),
    path("tasks/<int:task_id>/cancel/", cancel_task),
    path("tasks/<int:task_id>/", task_detail),
    path("tasks/<int:task_id>/update/", update_task),
    path("tasks/<int:task_id>/delete/", delete_task),
    path("users/register/", register_user),
    path("users/login/", login_user),
    path("users/me/", current_user),
    path("users/jwt/me/", jwt_me),
    path("users/logout/", logout_user),
    path(
        "users/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "users/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
]
