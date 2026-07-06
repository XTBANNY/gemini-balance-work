# Gemini Balance WorkBuddy 兼容版部署说明

这是给 WorkBuddy 使用的 Gemini API 聚合与 OpenAI 兼容代理服务，基于 `snailyp/gemini-balance` 修改。

本版本重点修复：

- WorkBuddy 工具调用中的 `strict`、`additionalProperties` 等 Gemini 不支持的 schema 字段。
- WorkBuddy 图片输入的 `image_url`、`input_image`、`input_text` 格式。
- Gemini 工具调用第二跳所需的 `thoughtSignature` 缓存和回填。
- OpenAI 兼容接口里的 `tool_choice` 对象格式。
- 工具调用响应的 `finish_reason=tool_calls`。

## WorkBuddy 配置

在 WorkBuddy 的自定义 OpenAI 兼容模型里填写：

```text
提供商: 自定义 / Custom
接口地址: http://<your-server-ip>:<your-port>/v1
API Key: <your-workbuddy-api-token>
模型名称: gemini-3.1-flash-lite
工具调用: 开启
图片输入: 开启
思考模式: 按需开启
```

如果旧会话已经报过工具调用错误，请新建一个 WorkBuddy 对话再测。旧会话里补丁前生成的工具调用没有缓存到 Gemini 的 `thoughtSignature`，直接重试可能继续失败。

## 原生部署步骤

以下步骤不用 Docker。

### 1. 安装依赖

```bash
apt-get update
apt-get install -y python3-pip python3-venv git nginx curl
```

### 2. 创建数据库

```bash
mysql -uroot <<'SQL'
CREATE DATABASE IF NOT EXISTS gemini_balance_work CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'gemini_balance'@'localhost' IDENTIFIED BY '<your-db-password>';
GRANT ALL PRIVILEGES ON gemini_balance_work.* TO 'gemini_balance'@'localhost';
FLUSH PRIVILEGES;
SQL
```

### 3. 拉取代码

```bash
mkdir -p /opt
git clone https://github.com/<your-github-user>/<your-repo>.git /opt/gemini-balance-work
cd /opt/gemini-balance-work
```

### 4. 创建 Python 环境

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 5. 写入环境变量

创建 `/opt/gemini-balance-work/.env`：

```env
DATABASE_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=gemini_balance
MYSQL_PASSWORD=<your-db-password>
MYSQL_DATABASE=gemini_balance_work

API_KEYS=["<your-gemini-api-key-1>","<your-gemini-api-key-2>"]
ALLOWED_TOKENS=["<your-workbuddy-api-token>"]
AUTH_TOKEN=<your-admin-token>

BASE_URL=https://generativelanguage.googleapis.com/v1beta
SHOW_THINKING_PROCESS=true
FAKE_STREAM_ENABLED=false
TOOLS_CODE_EXECUTION_ENABLED=false
URL_CONTEXT_ENABLED=false
TZ=Asia/Shanghai
LOG_LEVEL=INFO
```

`API_KEYS` 和 `ALLOWED_TOKENS` 必须是 JSON 数组字符串。不要把真实 `.env` 提交到 GitHub。

### 6. 创建 systemd 服务

创建 `/etc/systemd/system/gemini-balance-work.service`：

```ini
[Unit]
Description=Gemini Balance WorkBuddy API
After=network.target mariadb.service
Wants=mariadb.service

[Service]
Type=simple
WorkingDirectory=/opt/gemini-balance-work
EnvironmentFile=/opt/gemini-balance-work/.env
ExecStart=/opt/gemini-balance-work/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
systemctl daemon-reload
systemctl enable gemini-balance-work
systemctl restart gemini-balance-work
systemctl status gemini-balance-work
```

### 7. 配置 Nginx

创建 `/etc/nginx/sites-available/gemini-balance-work`：

```nginx
server {
    listen <your-public-port>;
    server_name <your-domain-or-server-ip>;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

启用配置：

```bash
ln -sfn /etc/nginx/sites-available/gemini-balance-work /etc/nginx/sites-enabled/gemini-balance-work
nginx -t
systemctl reload nginx
```

## 测试命令

健康检查：

```bash
curl http://127.0.0.1:8000/health
curl http://<your-server-ip>:<your-port>/health
```

模型列表：

```bash
curl http://<your-server-ip>:<your-port>/v1/models \
  -H "Authorization: Bearer <your-workbuddy-api-token>"
```

普通聊天：

```bash
curl http://<your-server-ip>:<your-port>/v1/chat/completions \
  -H "Authorization: Bearer <your-workbuddy-api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-lite",
    "messages": [{"role": "user", "content": "ping"}],
    "stream": false
  }'
```

工具调用 schema 测试：

```bash
curl http://<your-server-ip>:<your-port>/v1/chat/completions \
  -H "Authorization: Bearer <your-workbuddy-api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-lite",
    "messages": [{"role": "user", "content": "Use the tool to check Paris weather."}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather",
        "strict": true,
        "parameters": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }],
    "tool_choice": {
      "type": "function",
      "function": {"name": "get_weather"}
    },
    "stream": false
  }'
```

## 维护命令

查看服务：

```bash
systemctl status gemini-balance-work
```

重启服务：

```bash
systemctl restart gemini-balance-work
```

查看日志：

```bash
journalctl -u gemini-balance-work -f
```

更新代码：

```bash
cd /opt/gemini-balance-work
git pull origin main
. .venv/bin/activate
pip install -r requirements.txt
systemctl restart gemini-balance-work
```

修改外部端口：

```bash
sed -i 's/listen <old-port>;/listen <new-port>;/g' /etc/nginx/sites-available/gemini-balance-work
nginx -t
systemctl reload nginx
```

修改 Gemini API Key：

```bash
mysql -ugemini_balance -p gemini_balance_work
```

然后更新 `t_settings` 表里的 `API_KEYS`：

```sql
UPDATE t_settings
SET value='["<your-gemini-api-key-1>","<your-gemini-api-key-2>"]', updated_at=NOW()
WHERE `key`='API_KEYS';
```

重启服务：

```bash
systemctl restart gemini-balance-work
```

## 安全提醒

- 不要把真实服务器 IP、域名、端口、API Key、数据库密码、GitHub Token 写进公开仓库。
- 如果任何 token 或 API Key 曾经出现在公开仓库、聊天记录或日志里，请轮换。
- `.env` 只应该存在服务器本地。
