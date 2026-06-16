# Campus Task Backend

[![Django CI](https://github.com/RGHRT/campus-task-backend/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/RGHRT/campus-task-backend/actions/workflows/ci.yml)

基于 Django 与 MySQL 开发的校园互助任务平台后端，为代取快递、资料打印、物品代购、校园跑腿等场景提供任务发布、接取、完成确认和状态管理功能。

项目采用 JWT 进行接口身份认证，使用 Django ORM 操作 MySQL 数据库，并通过数据库事务与行级锁避免任务被重复接取。目前已完成 Swagger 接口文档、29 项自动化测试及 Railway 线上部署。

## 在线体验

* 项目入口：https://campus-task-backend-production.up.railway.app/
* Swagger UI：https://campus-task-backend-production.up.railway.app/api/docs/
* OpenAPI Schema：https://campus-task-backend-production.up.railway.app/api/schema/
* GitHub 仓库：https://github.com/RGHRT/campus-task-backend

项目根地址会自动跳转至 Swagger 接口文档。

> 在线环境仅用于项目演示，请勿提交真实个人信息或敏感数据。

## 项目功能

### 用户模块

* 用户注册
* Session 登录与退出
* JWT 登录认证
* Access Token 与 Refresh Token
* Refresh Token 刷新 Access Token
* 获取当前登录用户信息
* 用户密码加密存储
* 登录状态及接口权限校验

### 任务模块

* 发布校园互助任务
* 查询任务列表
* 查询任务详情
* 修改尚未被接取的任务
* 接取任务
* 接单者提交任务完成
* 发布者确认任务完成
* 取消尚未被接取的任务
* 删除已取消任务
* 查询当前用户发布的任务
* 查询当前用户接取的任务
* 按任务状态筛选
* 按标题或描述关键词搜索
* 分页查询任务

## 任务状态流程

任务的主要状态流转如下：

```text
未完成
  ↓ 接取任务
进行中
  ↓ 接单者提交完成
待确认
  ↓ 发布者确认完成
已完成
```

任务未被接取时，也可以由发布者执行：

```text
未完成 → 已取消 → 删除
```

## 业务规则

* 用户登录后才能发布、修改、接取或操作任务。
* 发布者不能接取自己发布的任务。
* 同一任务只能被一个用户接取。
* 只有任务接单者才能提交任务完成。
* 只有任务发布者才能确认任务完成。
* 任务被接取后不能再修改标题、描述和报酬。
* 已被接取的任务不能直接取消或删除。
* 只有已取消的任务才允许物理删除。
* 客户端发布任务时不能自行指定任务状态。
* 使用数据库事务与 `select_for_update()` 行级锁降低并发重复接单风险。

## 技术栈

### 后端

* Python 3.11
* Django 5.2
* Django REST Framework
* Simple JWT
* drf-spectacular
* python-dotenv

### 数据库

* MySQL 8.0
* Django ORM
* mysqlclient

### 测试与文档

* Django TestCase
* Swagger UI
* OpenAPI 3 Schema
* 29 项自动化测试

### 部署与工程化

* Railway
* Gunicorn
* WhiteNoise
* Git
* GitHub
* 环境变量配置
* 多分支开发流程

## 项目结构

```text
campus-task-backend/
├── api/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_task_publisher.py
│   │   ├── 0003_task_receiver.py
│   │   └── 0004_alter_task_status.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── response.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── campus_backend/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── .env.example
├── .gitignore
├── manage.py
├── railway.json
├── requirements.txt
├── schema.yaml
└── README.md
```

## 核心数据模型

任务模型主要包含以下字段：

| 字段            | 说明     |
| ------------- | ------ |
| `publisher`   | 任务发布者  |
| `receiver`    | 任务接单者  |
| `title`       | 任务标题   |
| `description` | 任务描述   |
| `reward`      | 任务报酬   |
| `status`      | 当前任务状态 |
| `created_at`  | 任务创建时间 |

任务状态包括：

```text
未完成
进行中
待确认
已完成
已取消
```

## 主要接口

### 用户接口

| 请求方式 | 接口地址                        | 功能              |
| ---- | --------------------------- | --------------- |
| POST | `/api/users/register/`      | 用户注册            |
| POST | `/api/users/login/`         | Session 登录      |
| POST | `/api/users/logout/`        | Session 退出      |
| GET  | `/api/users/me/`            | 获取 Session 登录用户 |
| POST | `/api/users/token/`         | 获取 JWT Token    |
| POST | `/api/users/token/refresh/` | 刷新 Access Token |
| GET  | `/api/users/jwt/me/`        | 获取 JWT 登录用户     |

### 任务接口

| 请求方式   | 接口地址                             | 功能       |
| ------ | -------------------------------- | -------- |
| GET    | `/api/tasks/`                    | 查询任务列表   |
| POST   | `/api/tasks/create/`             | 发布任务     |
| GET    | `/api/tasks/mine/`               | 查询我发布的任务 |
| GET    | `/api/tasks/received/`           | 查询我接取的任务 |
| GET    | `/api/tasks/{task_id}/`          | 查询任务详情   |
| PUT    | `/api/tasks/{task_id}/update/`   | 修改任务     |
| DELETE | `/api/tasks/{task_id}/delete/`   | 删除已取消任务  |
| POST   | `/api/tasks/{task_id}/accept/`   | 接取任务     |
| POST   | `/api/tasks/{task_id}/complete/` | 接单者提交完成  |
| POST   | `/api/tasks/{task_id}/confirm/`  | 发布者确认完成  |
| POST   | `/api/tasks/{task_id}/cancel/`   | 取消任务     |

完整请求参数和返回格式可在 Swagger 页面中查看。

## JWT 使用方式

### 获取 Token

请求：

```http
POST /api/users/token/
Content-Type: application/json
```

请求体：

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

成功后返回：

```json
{
  "refresh": "refresh_token",
  "access": "access_token"
}
```

### 携带 Access Token

访问受保护接口时，请在请求头中加入：

```http
Authorization: Bearer access_token
```

### 刷新 Access Token

请求：

```http
POST /api/users/token/refresh/
Content-Type: application/json
```

请求体：

```json
{
  "refresh": "refresh_token"
}
```

## 统一响应格式

项目普通业务接口采用统一 JSON 响应结构。

成功示例：

```json
{
  "code": 200,
  "message": "任务创建成功",
  "data": {
    "id": 1,
    "title": "帮取快递",
    "status": "未完成"
  }
}
```

失败示例：

```json
{
  "code": 401,
  "message": "请先登录",
  "data": null
}
```

## 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/RGHRT/campus-task-backend.git
cd campus-task-backend
```

### 2. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 4. 创建 MySQL 数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE campus_tasks
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;
```

建议创建项目专用数据库用户，不要直接使用 `root` 连接 Django。

### 5. 配置环境变量

复制：

```text
.env.example
```

创建：

```text
.env
```

配置示例：

```env
DJANGO_SECRET_KEY='replace-with-your-secret-key'
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=

MYSQL_DATABASE=campus_tasks
MYSQL_USER=campus_user
MYSQL_PASSWORD='replace-with-your-database-password'
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

真实的 `.env` 已加入 `.gitignore`，不要上传到 GitHub。

### 6. 执行数据库迁移

```powershell
python manage.py migrate
```

### 7. 启动项目

```powershell
python manage.py runserver 8001
```

浏览器打开：

```text
http://127.0.0.1:8001/
```

项目会自动跳转至：

```text
http://127.0.0.1:8001/api/docs/
```

## 自动化测试

运行全部测试：

```powershell
python manage.py test api
```

当前测试数量：

```text
29 项
```

测试覆盖内容包括：

* 用户注册成功
* 重复用户名校验
* 用户登录成功
* 错误密码登录失败
* JWT Token 获取
* Refresh Token 刷新
* JWT 用户接口权限
* 未登录用户发布任务限制
* Session 发布任务
* JWT 发布任务
* 发布者不能接取自己的任务
* Session 接取任务
* JWT 接取任务
* 重复接取任务限制
* 非接单者不能提交完成
* Session 提交任务完成
* JWT 提交任务完成
* 发布者确认完成
* JWT 确认完成
* 任务取消
* JWT 取消任务
* 未取消任务不能删除
* 删除已取消任务
* JWT 删除任务
* JWT 修改任务
* JWT 查询个人发布任务
* JWT 查询个人接取任务
* 搜索、筛选与分页
* 核心任务状态流转

## OpenAPI Schema 校验

生成并校验 OpenAPI 文档：

```powershell
python manage.py spectacular --file schema.yaml --validate
```

没有输出 Warning 或 Error，表示 Schema 校验通过。

## 静态文件

生产环境使用 WhiteNoise 提供 Django Admin 和 Swagger 的静态资源。

手动收集静态文件：

```powershell
python manage.py collectstatic --noinput
```

生成的 `staticfiles/` 目录不会提交到 Git。

## 部署说明

项目已部署至 Railway。

部署过程包括：

```text
安装 requirements.txt
→ 收集静态文件
→ 执行数据库迁移
→ Gunicorn 启动 Django
→ 连接 Railway MySQL
```

Railway 启动命令：

```bash
gunicorn campus_backend.wsgi:application --bind 0.0.0.0:$PORT
```

部署前命令：

```bash
python manage.py migrate
```

构建命令：

```bash
python manage.py collectstatic --noinput
```

## 项目亮点

### 完整业务闭环

项目不是简单的任务增删改查，而是实现了从发布到完成确认的完整状态流转。

### 多角色权限控制

针对发布者、接单者和普通登录用户分别设置操作权限，防止越权修改任务状态。

### 并发接单处理

接取、提交完成、确认和取消等关键操作使用：

```python
transaction.atomic()
select_for_update()
```

对任务记录加行级锁，降低两个用户同时接取同一任务造成的数据冲突风险。

### JWT 身份认证

实现 Access Token、Refresh Token、Token 刷新和 JWT 保护接口，适用于前后端分离项目。

### 自动化测试

通过 29 项自动化测试验证用户模块、任务状态流转、权限控制、JWT 认证和分页搜索等核心功能。

### 在线接口文档

使用 drf-spectacular 自动生成 OpenAPI Schema 和 Swagger UI，可直接在线调试接口。

### 配置安全

使用 `.env` 管理 Django 密钥和数据库密码，敏感信息不会提交至 GitHub。

## 当前状态

已完成：

* 用户注册与登录
* Session 身份认证
* JWT 身份认证
* Token 刷新
* 完整任务状态流转
* 权限控制
* MySQL 数据持久化
* 搜索、筛选和分页
* 数据库事务与行级锁
* Swagger / OpenAPI 文档
* 29 项自动化测试
* GitHub 版本管理
* Railway 线上部署
* Gunicorn 生产服务器
* WhiteNoise 静态文件服务
* HTTPS 与生产环境安全配置

后续可扩展：

* JWT Token 黑名单与主动注销
* Redis 缓存
* 接口访问频率限制
* 消息通知
* 任务评价系统
* 图片与附件上传
* Docker 与 Docker Compose
* GitHub Actions 持续集成
* 操作日志与异常监控

## 作者

赵锦城

武汉大学遥感信息工程学院
