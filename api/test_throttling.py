import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase


class ThrottlingApiTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_register_rate_limit(self):
        payload = {
            "username": "rate_register_user",
            "password": "123456",
            "email": "rate_register@example.com",
        }

        for _ in range(5):
            self.client.post(
                "/api/users/register/",
                data=json.dumps(payload),
                content_type="application/json",
            )

        response = self.client.post(
            "/api/users/register/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)

    def test_session_login_rate_limit(self):
        User.objects.create_user(
            username="rate_login_user",
            password="123456",
        )
        payload = {
            "username": "rate_login_user",
            "password": "wrong-password",
        }

        for _ in range(10):
            self.client.post(
                "/api/users/login/",
                data=json.dumps(payload),
                content_type="application/json",
            )

        response = self.client.post(
            "/api/users/login/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)

    def test_jwt_login_rate_limit(self):
        User.objects.create_user(
            username="rate_jwt_user",
            password="123456",
        )
        payload = {
            "username": "rate_jwt_user",
            "password": "wrong-password",
        }

        for _ in range(10):
            self.client.post(
                "/api/users/token/",
                data=json.dumps(payload),
                content_type="application/json",
            )

        response = self.client.post(
            "/api/users/token/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)

    def test_task_create_rate_limit(self):
        user = User.objects.create_user(
            username="rate_task_user",
            password="123456",
        )
        self.client.force_login(user)

        payload = {
            "title": "限流测试任务",
            "description": "用于验证任务发布接口限流",
            "reward": "1.00",
        }

        for _ in range(5):
            response = self.client.post(
                "/api/tasks/create/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/tasks/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)
