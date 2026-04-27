# MBTI-Research

一个基于 Django 的 AI 科研协作偏好测评系统，支持登录、分页答题、进度自动保存、结果计算与 PDF 导出。题目和结果解释面向硕士研究生、研究助理、博士后和科研助理教授等科研团队成员。

## 🌐 在线体验

部署后可通过你的服务器公网地址或域名访问，例如：

```text
http://你的服务器公网IP:8000/
```

无需安装，直接在线完成 MBTI-Research 测评，了解你的科研协作画像、沟通方式和适合承担的研究角色。

---

## 🚀 功能特性
- 用户注册、登录、登出，统一的消息提示（成功/失败原因）
- MBTI-Research 测评分页（每页 10 题），返回上一页保留答案
- 自动保存答题进度（Session 存储，跨页不丢失）
- 完成度与进度条展示，未完成时友好提示定位
- 结果计算与类型码生成（如 INTJ），维度置信度与详情展示
- 导出测评结果为 PDF 报告（ReportLab，可选安装）
- 密码输入眼睛图标显示/隐藏，与输入框右侧对齐


## 🛠️ 技术栈
- 后端：Django 5.2.6
- 前端：HTML5、CSS3、JavaScript（Bootstrap 5 样式）
- 数据库：SQLite（开发环境）
- PDF：ReportLab（可选）

## 📋 系统要求
- Python 3.11+（推荐）
- Django 5.2+
- 现代浏览器（Chrome / Firefox / Edge）

## 🔧 安装与配置
### 1. 进入项目目录并创建虚拟环境
```bash
cd mbti-test
python -m venv venv
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # macOS/Linux
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```
> 说明：`reportlab` 为 PDF 导出所需的可选依赖，若不需要 PDF 功能可不安装。

### 3. 数据库迁移
数据库迁移是 Django 管理数据库结构变更的方式，需要按顺序执行：

```bash
# 生成迁移文件（检测模型变化）
python manage.py makemigrations

# 执行迁移（将迁移应用到数据库）
python manage.py migrate
```

**迁移说明**：
- `makemigrations`：扫描模型定义的变化，生成迁移文件（保存在 `mbti/migrations/` 目录）
- `migrate`：执行所有未应用的迁移，更新数据库结构
- 首次运行会创建所有必要的表结构
- 后续模型变更时，需要先运行 `makemigrations` 再运行 `migrate`

### 4. 数据库初始化与数据导入

项目提供了完整的数据库管理脚本来初始化数据和导入题库：

#### 4.1 完整初始化流程（推荐）

```bash
# 1. 确保已激活虚拟环境
# source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate     # Windows

# 2. 清空数据库（可选，如果需要完全重置）
python database_management/clear_database.py

# 3. 初始化数据库（导入 MBTI-Research 93题题库 + 创建管理员账号）
python database_management/init_database.py

# 4. 导入16种科研协作画像详细数据（可选，推荐）
python database_management/populate_personality_data.py
```

#### 4.2 数据库管理脚本说明

**`clear_database.py`** - 清空数据库
- 清空所有测试相关数据（题目、回答、结果、用户等）
- 保留超级用户账号
```bash
python database_management/clear_database.py
```

**`init_database.py`** - 初始化数据库
- 导入 MBTI-Research 93题题库（从JSON文件）
- 创建Django后台管理员账号（用户名：`admin`，密码：`admin@123..`）
```bash
python database_management/init_database.py
```

**`add_questions_from_json.py`** - 仅导入题库
- 从JSON格式文件导入 MBTI-Research 93题题库
- 不创建管理员账号（推荐使用此脚本单独导入题库）
```bash
python database_management/add_questions_from_json.py
```
> **注意**：这是推荐的题库导入方式，使用JSON格式更清晰易维护。

**`populate_personality_data.py`** - 导入科研协作画像数据
- 导入16种 MBTI-Research 科研协作画像的详细描述数据
- 包含丰富的描述信息（科研偏好特点、研究工作风格、团队协作方式、科研角色建议等）
- 使用 `get_or_create`，可安全重复执行
```bash
python database_management/populate_personality_data.py
```

**`validate_scoring_rules.py`** - 验证计分规则
- 验证标准MBTI 93题的计分规则是否正确
```bash
python database_management/validate_scoring_rules.py
```

#### 4.3 管理员账号

初始化数据库后会自动创建管理员账号：
- **用户名**：`admin`
- **密码**：`admin@123..`
- **访问地址**：`http://127.0.0.1:8000/admin/`

> **注意**：官方 MBTI 题库与评估工具受版权与商标保护，禁止在未经授权的情况下复刻。当前题库为开放版、结构兼容的替代方案，使用标准MBTI 93题计分规则，评分逻辑位于 `mbti/services_standard.py`。

### 5. 启动开发服务器
```bash
python manage.py runserver 127.0.0.1:8000
```
访问 `http://127.0.0.1:8000`。

## 📁 项目结构
```
mbti-test/
├── manage.py                    # Django 管理脚本
├── requirements.txt             # Python 依赖包
├── db.sqlite3                   # SQLite 数据库（开发环境）
├── mbti_site/                   # 项目配置目录
│   ├── settings.py              # Django 设置
│   ├── urls.py                  # 主路由配置
│   ├── middleware.py            # 自定义中间件（session隔离）
│   └── wsgi.py                  # WSGI 配置
├── mbti/                        # MBTI 应用
│   ├── models.py                # 数据模型（Question, Response, Result, TypeProfile等）
│   ├── views.py                 # 视图函数（测试、保存、提交、结果、PDF导出）
│   ├── urls.py                  # MBTI 路由配置
│   ├── services_standard.py     # 标准MBTI计分服务
│   ├── admin.py                 # Django后台管理配置
│   └── migrations/              # 数据库迁移文件
├── users/                       # 用户应用
│   ├── models.py                # 用户模型（使用Django默认User）
│   ├── views.py                 # 视图函数（登录、注册、登出、修改密码）
│   ├── forms.py                 # 表单（登录、注册）
│   └── urls.py                  # 用户路由配置
├── database_management/         # 数据库管理脚本
│   ├── init_database.py         # 初始化数据库（导入题库+创建管理员）
│   ├── clear_database.py        # 清空数据库
│   ├── add_questions_from_json.py  # 从JSON导入题库
│   ├── populate_personality_data.py # 导入16种科研协作画像数据
│   └── validate_scoring_rules.py   # 验证计分规则
├── data/                        # 数据文件目录
│   └── questions_standard_mbti_93.json  # 标准MBTI 93题JSON格式题库
├── templates/                   # 模板文件
│   ├── base.html                # 基础模板
│   ├── users/                   # 用户相关模板
│   │   ├── login.html
│   │   ├── register.html
│   │   └── password_change.html
│   └── mbti/                    # MBTI相关模板
│       ├── home.html
│       ├── test.html
│       └── result.html
├── static/                      # 静态文件
│   └── css/
│       └── style.css            # 样式文件
└── screenshots/                 # 项目截图
```

## 🧭 使用指南
### 1. 登录与注册
- 进入登录或注册页，密码框右侧有眼睛图标可切换显示/隐藏。
- 登录成功或失败（如用户名/密码错误）将通过顶部消息区域进行提示。

### 2. 进行 MBTI 测试
- 每页 10 题，可点击“下一页/上一页”。
- 选择选项会自动保存到 Session；返回上一页不会丢失选择。
- 未完成当前页题目时，点击下一步会弹出提示并定位到未完成题目。

### 3. 提交与结果
- 提交前需完成所有题目，系统会校验并提示缺失数量。
- 结果页显示四维度分数与倾向，生成类型码（如 `INTJ`）。
- 可将结果导出为 PDF 报告（需安装 `reportlab`）。

## 📝 API 文档

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 主页或入口（按项目配置） |
| `/mbti/` | GET | MBTI 首页 |
| `/mbti/test/` | GET | 测试页（支持分页） |
| `/mbti/save-progress/` | POST | 保存作答进度（AJAX，会话存储） |
| `/mbti/submit/` | POST | 提交答案并计算结果 |
| `/mbti/result/` | GET | 结果展示 |

## 📊 结果计算说明
本项目使用**标准MBTI 93题计分规则**：
- **计分方式**：每题选择A或B，按照标准MBTI规则累加维度分数
- **四个维度**：IE（外向-内向）、SN（感觉-直觉）、TF（思考-情感）、JP（判断-知觉）
- **类型判定**：每个维度选择分数较高的一方，同分时按规则选择（E/I同分选I，S/N同分选N，T/F同分选F，J/P同分选P）
- **置信度计算**：基于各维度的分数差异，用于评估结果的可靠性
- 详细计分逻辑参见 `mbti/services_standard.py`

## 🔐 安全特性
- CSRF 保护、会话管理
- 密码哈希存储
- 基于消息框的统一错误与成功提示

## ❗ 常见问题

**PDF 字体乱码**：
- Windows 下系统会自动尝试注册常见中文字体
- 如仍出现乱码，可在代码中自定义字体路径（修改 `mbti/views.py` 中的 `result_pdf_view` 函数）

**静态文件**：
- 开发环境确保 `DEBUG=True`，Django会自动处理静态文件
- 生产环境需运行 `python manage.py collectstatic` 收集静态文件并配置服务器

**数据库问题**：
- 如果数据库迁移出错，可以删除 `db.sqlite3` 和 `mbti/migrations/` 目录下除 `__init__.py` 外的文件，然后重新运行 `makemigrations` 和 `migrate`

## 🚀 生产部署（示例）
```bash
pip install gunicorn
python manage.py collectstatic --noinput
# 示例：WSGI + 反向代理（略）
```

## ⬆️ 提交到 GitHub（SSH 方式）
以下步骤在 Windows PowerShell 中执行：
- 生成 SSH Key（推荐 Ed25519）：
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```
- 将公钥内容（`%USERPROFILE%\.ssh\id_ed25519.pub`）添加到 GitHub：Settings → SSH and GPG keys → New SSH key。
- 验证连接：
```bash
ssh -T git@github.com
```
- 在项目根目录初始化并设置远程为 SSH：
```bash
cd mbti-test
git init
git config user.name "Your Name"
git config user.email "your_email@example.com"
# 新仓库：
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
# 若已有远程（HTTPS），改为 SSH：
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```
- 提交与推送：
```bash
git add -A
git commit -m "docs: 更新题库与类型导入说明，新增 SSH 提交指南"
git branch -M main
git push -u origin main
```


## 📄 许可证
本项目采用 MIT 许可证。

## 🙏 致谢
- 感谢原作者张超武及原项目 `zcw576020095/mbti-test` 提供的 Django 项目基础与实现参考
- Django 社区
- Bootstrap 团队
- ReportLab 项目

---
⭐ 如果这个项目对你有帮助，请给它一个星标！
