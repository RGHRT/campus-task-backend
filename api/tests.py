import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Task


class UserApiTests(TestCase):

    def test_register_user_success(self):
        """测试用户注册成功"""

        request_data = {
            "username": "testuser",
            "password": "123456",
            "email": "testuser@example.com"
        }

        response = self.client.post(
            "/api/users/register/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "用户注册成功"
        )

        self.assertTrue(
            User.objects.filter(
                username="testuser"
            ).exists()
        )

        user = User.objects.get(
            username="testuser"
        )

        self.assertEqual(
            user.email,
            "testuser@example.com"
        )

        self.assertTrue(
            user.check_password("123456")
        )

    def test_register_duplicate_username(self):
        """测试重复用户名不能注册"""

        User.objects.create_user(
            username="testuser",
            password="123456",
            email="old@example.com"
        )

        request_data = {
            "username": "testuser",
            "password": "654321",
            "email": "new@example.com"
        }

        response = self.client.post(
            "/api/users/register/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        response_data = response.json()

        self.assertEqual(response_data["code"], 400)
        self.assertEqual(
            response_data["message"],
            "用户名已存在"
        )

        self.assertEqual(
            User.objects.filter(
                username="testuser"
            ).count(),
            1
        )

    def test_login_user_success(self):
        """测试用户使用正确密码登录成功"""

        user = User.objects.create_user(
            username="loginuser",
            password="123456",
            email="loginuser@example.com"
        )

        request_data = {
            "username": "loginuser",
            "password": "123456"
        }

        response = self.client.post(
            "/api/users/login/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "用户登录成功"
        )
        self.assertEqual(
            response_data["data"]["username"],
            "loginuser"
        )
        self.assertEqual(
            response_data["data"]["email"],
            "loginuser@example.com"
        )

        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(user.id)
        )

    def test_login_user_wrong_password(self):
        """测试使用错误密码登录失败"""

        User.objects.create_user(
            username="loginuser",
            password="123456",
            email="loginuser@example.com"
        )

        request_data = {
            "username": "loginuser",
            "password": "111111"
        }

        response = self.client.post(
            "/api/users/login/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        response_data = response.json()

        self.assertEqual(response_data["code"], 400)
        self.assertEqual(
            response_data["message"],
            "用户名或密码错误"
        )
        self.assertIsNone(response_data["data"])

    def test_jwt_token_obtain_success(self):
        """测试使用用户名和密码获取JWT令牌"""

        User.objects.create_user(
            username="jwt_user",
            email="jwt_user@example.com",
            password="JwtTest@123456",
        )

        response = self.client.post(
            "/api/users/token/",
            {
                "username": "jwt_user",
                "password": "JwtTest@123456",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertIn("access", response_data)
        self.assertIn("refresh", response_data)


    def test_jwt_token_refresh_success(self):
        """测试使用refresh令牌获取新的access令牌"""

        User.objects.create_user(
            username="jwt_refresh_user",
            email="jwt_refresh_user@example.com",
            password="JwtTest@123456",
        )

        token_response = self.client.post(
            "/api/users/token/",
            {
                "username": "jwt_refresh_user",
                "password": "JwtTest@123456",
            },
            content_type="application/json",
        )

        refresh_token = token_response.json()["refresh"]

        refresh_response = self.client.post(
            "/api/users/token/refresh/",
            {
                "refresh": refresh_token,
            },
            content_type="application/json",
        )

        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("access", refresh_response.json())

    def test_jwt_me_requires_token(self):
        """测试未携带JWT时不能获取当前用户"""

        response = self.client.get(
            "/api/users/jwt/me/"
        )

        self.assertEqual(response.status_code, 401)


    def test_jwt_me_returns_current_user(self):
        """测试携带有效JWT时可以获取当前用户"""

        User.objects.create_user(
            username="jwt_me_user",
            email="jwt_me_user@example.com",
            password="JwtTest@123456",
        )

        token_response = self.client.post(
            "/api/users/token/",
            {
                "username": "jwt_me_user",
                "password": "JwtTest@123456",
            },
            content_type="application/json",
        )

        access_token = token_response.json()["access"]

        response = self.client.get(
            "/api/users/jwt/me/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["data"]["username"],
            "jwt_me_user",
        )

class TaskApiTests(TestCase):

    def setUp(self):
        """每个任务测试开始前创建两个用户"""

        self.publisher = User.objects.create_user(
            username="publisher",
            password="123456",
            email="publisher@example.com"
        )

        self.receiver = User.objects.create_user(
            username="receiver",
            password="123456",
            email="receiver@example.com"
        )

    def test_create_task_requires_login(self):
        """测试未登录用户不能发布任务"""

        request_data = {
            "title": "帮取快递",
            "description": "帮忙从快递站取一个快递",
            "reward": 5
        }

        response = self.client.post(
            "/api/tasks/create/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 401)

        response_data = response.json()

        self.assertEqual(response_data["code"], 401)
        self.assertEqual(
            response_data["message"],
            "请先登录后再发布任务"
        )

        self.assertEqual(Task.objects.count(), 0)

    def test_create_task_success(self):
        """测试登录用户可以发布任务"""

        self.client.force_login(self.publisher)

        request_data = {
            "title": "帮取快递",
            "description": "帮忙从快递站取一个快递",
            "reward": "5.50",
            "status": "已完成"
        }

        response = self.client.post(
            "/api/tasks/create/",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务创建成功"
        )

        task = Task.objects.get(
            title="帮取快递"
        )

        self.assertEqual(
            task.publisher,
            self.publisher
        )

        self.assertEqual(
            task.status,
            Task.Status.PENDING
        )

        self.assertIsNone(task.receiver)

    def test_publisher_cannot_accept_own_task(self):
        """测试发布者不能接取自己发布的任务"""

        task = Task.objects.create(
            publisher=self.publisher,
            title="帮带早餐",
            description="帮忙从食堂带一份早餐",
            reward=4,
            status=Task.Status.PENDING
        )

        self.client.force_login(self.publisher)

        response = self.client.post(
            f"/api/tasks/{task.id}/accept/"
        )

        self.assertEqual(response.status_code, 403)

        response_data = response.json()

        self.assertEqual(response_data["code"], 403)
        self.assertEqual(
            response_data["message"],
            "不能接取自己发布的任务"
        )

        task.refresh_from_db()

        self.assertIsNone(task.receiver)
        self.assertEqual(
            task.status,
            Task.Status.PENDING
        )

    def test_accept_task_success(self):
        """测试其他用户可以成功接取任务"""

        task = Task.objects.create(
            publisher=self.publisher,
            title="帮带早餐",
            description="帮忙从食堂带一份早餐",
            reward=4,
            status=Task.Status.PENDING
        )

        self.client.force_login(self.receiver)

        response = self.client.post(
            f"/api/tasks/{task.id}/accept/"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务接取成功"
        )

        task.refresh_from_db()

        self.assertEqual(
            task.receiver,
            self.receiver
        )

        self.assertEqual(
            task.status,
            Task.Status.IN_PROGRESS
        )

        self.assertEqual(
            response_data["data"]["receiver"]["username"],
            "receiver"
        )

    def test_task_cannot_be_accepted_twice(self):
        """测试已经被接取的任务不能重复接取"""

        task = Task.objects.create(
            publisher=self.publisher,
            receiver=self.receiver,
            title="帮取资料",
            description="帮忙取一份课程资料",
            reward=3,
            status=Task.Status.IN_PROGRESS
        )

        another_receiver = User.objects.create_user(
            username="another_receiver",
            password="123456",
            email="another@example.com"
        )

        self.client.force_login(another_receiver)

        response = self.client.post(
            f"/api/tasks/{task.id}/accept/"
        )

        self.assertEqual(response.status_code, 409)

        response_data = response.json()

        self.assertEqual(response_data["code"], 409)
        self.assertEqual(
            response_data["message"],
            "该任务已经被接取"
        )

        task.refresh_from_db()

        self.assertEqual(task.receiver, self.receiver)
        self.assertEqual(
            task.status,
            Task.Status.IN_PROGRESS
        )

    def test_non_receiver_cannot_complete_task(self):
        """测试非接单者不能提交任务完成"""

        task = Task.objects.create(
            publisher=self.publisher,
            receiver=self.receiver,
            title="帮取图书",
            description="帮忙从图书馆取一本书",
            reward=5,
            status=Task.Status.IN_PROGRESS
        )

        self.client.force_login(self.publisher)

        response = self.client.post(
            f"/api/tasks/{task.id}/complete/"
        )

        self.assertEqual(response.status_code, 403)

        response_data = response.json()

        self.assertEqual(response_data["code"], 403)
        self.assertEqual(
            response_data["message"],
            "只有接单者才能提交任务完成"
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            Task.Status.IN_PROGRESS
        )

    def test_receiver_complete_task_success(self):
        """测试接单者可以提交任务完成"""

        task = Task.objects.create(
            publisher=self.publisher,
            receiver=self.receiver,
            title="帮带早餐",
            description="帮忙从食堂带一份早餐",
            reward=4,
            status=Task.Status.IN_PROGRESS
        )

        self.client.force_login(self.receiver)

        response = self.client.post(
            f"/api/tasks/{task.id}/complete/"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务已提交完成，等待发布者确认"
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            Task.Status.WAITING_CONFIRM
        )

    def test_publisher_confirm_task_success(self):
        """测试发布者可以确认任务完成"""

        task = Task.objects.create(
            publisher=self.publisher,
            receiver=self.receiver,
            title="帮打印地图",
            description="帮忙打印一张课程作业地图",
            reward=6,
            status=Task.Status.WAITING_CONFIRM
        )

        self.client.force_login(self.publisher)

        response = self.client.post(
            f"/api/tasks/{task.id}/confirm/"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务已确认完成"
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            Task.Status.COMPLETED
        )

    def test_cancel_task_success(self):
        """测试发布者可以取消尚未被接取的任务"""

        task = Task.objects.create(
            publisher=self.publisher,
            title="测试取消任务",
            description="用于测试任务取消功能",
            reward=2,
            status=Task.Status.PENDING
        )

        self.client.force_login(self.publisher)

        response = self.client.post(
            f"/api/tasks/{task.id}/cancel/"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务取消成功"
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            Task.Status.CANCELLED
        )

    def test_task_cannot_be_deleted_before_cancel(self):
        """测试未取消的任务不能直接删除"""

        task = Task.objects.create(
            publisher=self.publisher,
            title="测试直接删除",
            description="未取消时不能直接删除",
            reward=2,
            status=Task.Status.PENDING
        )

        self.client.force_login(self.publisher)

        response = self.client.delete(
            f"/api/tasks/{task.id}/delete/"
        )

        self.assertEqual(response.status_code, 409)

        response_data = response.json()

        self.assertEqual(response_data["code"], 409)
        self.assertEqual(
            response_data["message"],
            "请先取消任务，再执行删除"
        )

        self.assertTrue(
            Task.objects.filter(id=task.id).exists()
        )

    def test_delete_cancelled_task_success(self):
        """测试发布者可以删除已经取消的任务"""

        task = Task.objects.create(
            publisher=self.publisher,
            title="测试删除已取消任务",
            description="任务取消后允许彻底删除",
            reward=2,
            status=Task.Status.CANCELLED
        )

        self.client.force_login(self.publisher)

        response = self.client.delete(
            f"/api/tasks/{task.id}/delete/"
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "任务删除成功"
        )

        self.assertFalse(
            Task.objects.filter(id=task.id).exists()
        )

    def test_task_list_filter_search_and_pagination(self):
        """测试任务列表的状态筛选、关键词搜索和分页"""

        Task.objects.create(
            publisher=self.publisher,
            title="帮带早餐",
            description="帮忙从食堂带一份早餐",
            reward=4,
            status=Task.Status.PENDING
        )

        Task.objects.create(
            publisher=self.publisher,
            title="帮买晚饭",
            description="帮忙从食堂带一份晚饭",
            reward=6,
            status=Task.Status.PENDING
        )

        Task.objects.create(
            publisher=self.publisher,
            title="资料打印",
            description="帮忙打印课程资料",
            reward=3,
            status=Task.Status.COMPLETED
        )

        response = self.client.get(
            "/api/tasks/",
            {
                "status": Task.Status.PENDING,
                "keyword": "食堂",
                "page": 1,
                "page_size": 1
            }
        )

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertEqual(response_data["code"], 200)
        self.assertEqual(
            response_data["message"],
            "获取任务列表成功"
        )

        data = response_data["data"]

        self.assertEqual(data["total"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 1)
        self.assertEqual(len(data["list"]), 1)

        self.assertIn(
            "食堂",
            data["list"][0]["description"]
        )

        self.assertEqual(
            data["list"][0]["status"],
            Task.Status.PENDING
        )