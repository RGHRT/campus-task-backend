# Campus Task Backend

基于 Django 和 MySQL 开发的校园互助任务平台后端，为校园内代取快递、资料打印、物品代购等互助场景提供任务发布、接取和状态管理功能。

## 项目功能

### 用户模块

* 用户注册
* 用户登录与退出
* 获取当前登录用户
* Session 身份认证
* 用户密码加密存储
* 登录权限校验

### 任务模块

* 发布校园互助任务
* 查询任务列表与任务详情
* 修改尚未被接取的任务
* 接取任务
* 提交任务完成
* 发布者确认完成
* 取消和删除任务
* 查询自己发布的任务
* 查询自己接取的任务
* 按任务状态筛选
* 按关键词搜索
* 分页查询

## 任务状态流程

```text
未完成
  ↓ 接取任务
进行中
  ↓ 接取者提交完成
待确认
  ↓ 发布者确认
已完成
```

未被接取的任务也可以执行：

```text
未完成 → 已取消 → 删除
```

## 业务规则

* 发布者不能接取自己发布的任务
* 同一任务只能被一个用户接取
* 只有任务接取者可以提交完成
* 只有任务发布者可以确认完成
* 已被接取的任务不能取消或删除
* 只有已取消的任务可以被物理删除
* 使用数据库事务和行级锁避免任务被重复接取

## 技术栈

* Python 3.11
* Django 5.2
* MySQL 8.0
* mysqlclient
* python-dotenv
* Django ORM
* Django TestCase
* Git / GitHub

## 自动化测试

项目目前包含 16 项自动化测试，覆盖：

* 用户注册与登录
* 登录权限验证
* 任务发布
* 任务接取
* 重复接取校验
* 任务完成与确认
* 任务取消与删除
* 搜索、筛选和分页

运行测试：

```bash
python manage.py test api
```

当前测试结果：

```text
Ran 16 tests
OK
```

## 项目结构

```text
campus-task-backend/
├── api/
│   ├── migrations/
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
├── requirements.txt
└── README.md
```

## 当前开发状态

已完成：

* 用户模块
* 任务完整业务流程
* 权限控制
* MySQL 数据库配置
* 环境变量配置
* 自动化测试
* GitHub 版本管理

后续计划：

* JWT 身份认证
* Swagger 接口文档
* 统一异常处理
* Redis 缓存
* Docker 部署
* 线上环境部署
