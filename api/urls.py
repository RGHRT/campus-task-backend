from django.urls import path

from .views import (
    hello,
    task_list,
    create_task,
    task_detail,
    update_task,
    delete_task,
    register_user,
    login_user,
    current_user,
    logout_user,
    my_received_task_list,
    my_task_list,
    accept_task,
    complete_task,
    confirm_task,
    cancel_task
)

urlpatterns = [
    path('hello/', hello),

    path('tasks/', task_list),
    path('tasks/create/', create_task),
    path('tasks/mine/', my_task_list),
    path('tasks/received/', my_received_task_list),
    path('tasks/<int:task_id>/accept/', accept_task),
    path('tasks/<int:task_id>/complete/', complete_task),
    path('tasks/<int:task_id>/confirm/', confirm_task),
    path('tasks/<int:task_id>/cancel/', cancel_task),
    path('tasks/<int:task_id>/', task_detail),
    path('tasks/<int:task_id>/update/', update_task),
    path('tasks/<int:task_id>/delete/', delete_task),

    path('users/register/', register_user),
    path('users/login/', login_user),
    path('users/me/', current_user),
    path('users/logout/', logout_user),
]