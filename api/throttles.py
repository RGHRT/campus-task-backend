from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class IpRateThrottle(SimpleRateThrottle):
    # 根据客户端 IP 地址进行限流。
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class LoginRateThrottle(IpRateThrottle):
    scope = "login"


class RegisterRateThrottle(IpRateThrottle):
    scope = "register"


class TaskCreateRateThrottle(UserRateThrottle):
    scope = "task_create"
