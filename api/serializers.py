def task_to_dict(task):
    publisher_data = None
    receiver_data = None

    if task.publisher is not None:
        publisher_data = {
            "id": task.publisher.id,
            "username": task.publisher.username
        }

    if task.receiver is not None:
        receiver_data = {
            "id": task.receiver.id,
            "username": task.receiver.username
        }

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "reward": str(task.reward),
        "status": task.status,
        "publisher": publisher_data,
        "receiver": receiver_data,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }
def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S")
    }