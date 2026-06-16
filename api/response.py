from django.http import JsonResponse


def success_response(data=None, message="操作成功"):
    return JsonResponse(
        {
            "code": 200,
            "message": message,
            "data": data
        },
        json_dumps_params={
            "ensure_ascii": False
        }
    )


def error_response(message="操作失败", code=400):
    return JsonResponse(
        {
            "code": code,
            "message": message,
            "data": None
        },
        status=code,
        json_dumps_params={
            "ensure_ascii": False
        }
    )