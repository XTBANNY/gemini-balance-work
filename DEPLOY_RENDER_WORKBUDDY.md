# Render 部署 WorkBuddy 兼容版 Gemini Balance

本分支基于 `snailyp/gemini-balance`，额外修复了 WorkBuddy 使用 OpenAI 兼容接口时的几个兼容问题：

- `tool_choice` 支持 OpenAI 客户端常见的对象格式。
- 图片输入兼容 `image_url`、`input_image`、`input_text`。
- 工具调用结果会转换为 Gemini 需要的 `functionResponse`。
- 递归清理 Gemini 不支持的工具 schema 字段，例如 `strict`、`additionalProperties`。
- 工具调用响应的 `finish_reason` 更接近 OpenAI 客户端预期。

## 1. 准备 GitHub 仓库

1. 在 GitHub 新建一个空仓库，例如 `gemini-balance-workbuddy`。
2. 把本项目源码推送到这个仓库。
3. 不要把 Gemini API Key、GitHub Token、Render 密码提交到仓库。

如果 GitHub Token 曾经发到聊天、日志、截图或公开页面中，请立刻在 GitHub 删除这个 Token，并重新生成。

## 2. 创建 Render 数据库

推荐使用 Render MySQL 兼容服务或外部 MySQL。如果你已经在旧项目中有数据库，可以继续复用。

记录下面信息：

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

如果你只想快速试用，也可以设置 `DATABASE_TYPE=sqlite`，并设置 `SQLITE_DATABASE=/tmp/gemini-balance.db`。但 Render 免费实例重启后本地文件可能丢失，不推荐长期使用。

## 3. 创建 Render Web Service

在 Render 控制台选择：

- New
- Web Service
- 连接你的 GitHub 仓库
- Runtime 选择 Docker
- Branch 选择 `main`

Render 会使用仓库里的 `Dockerfile` 构建服务。

## 4. Render 环境变量

至少需要配置：

```env
DATABASE_TYPE=mysql
MYSQL_HOST=你的数据库地址
MYSQL_PORT=3306
MYSQL_USER=你的数据库用户名
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=你的数据库名

API_KEYS=["你的 Gemini API Key 1","你的 Gemini API Key 2"]
ALLOWED_TOKENS=["zhang1202"]
AUTH_TOKEN=zhang1202

BASE_URL=https://generativelanguage.googleapis.com/v1beta
SHOW_THINKING_PROCESS=true
FAKE_STREAM_ENABLED=false
TOOLS_CODE_EXECUTION_ENABLED=false
URL_CONTEXT_ENABLED=false
TZ=Asia/Shanghai
```

说明：

- `API_KEYS` 必须是 JSON 数组字符串。
- `ALLOWED_TOKENS` 是给 WorkBuddy 使用的 API Key，也必须是 JSON 数组字符串。
- `AUTH_TOKEN` 是后台管理密码。可以和 `ALLOWED_TOKENS[0]` 一样，也可以单独设置。
- WorkBuddy 里填写的 API Key 就是 `ALLOWED_TOKENS` 里的值。

## 5. 部署后检查

假设你的 Render 域名是：

```text
https://your-service.onrender.com
```

检查模型列表：

```bash
curl https://your-service.onrender.com/v1/models \
  -H "Authorization: Bearer zhang1202"
```

检查普通聊天：

```bash
curl https://your-service.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer zhang1202" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-lite",
    "messages": [{"role": "user", "content": "ping"}],
    "stream": false
  }'
```

检查工具调用 schema 清理：

```bash
curl https://your-service.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer zhang1202" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-lite",
    "messages": [{"role": "user", "content": "调用工具查询 Paris 天气"}],
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

如果这一步不再出现 `Unknown name "additionalProperties"` 或 `Unknown name "strict"`，说明工具 schema 兼容修复生效。

## 6. WorkBuddy 配置

在 WorkBuddy 模型配置里填写：

- 提供商：自定义 / Custom
- 接口地址：`https://your-service.onrender.com/v1`
- API Key：`zhang1202` 或你设置在 `ALLOWED_TOKENS` 里的值
- 模型名称：`gemini-3.1-flash-lite`
- 工具调用：开启
- 图片输入：开启
- 思考模式：按需开启

如果你使用自定义域名，例如：

```text
https://gbapi.818sx.com
```

则 WorkBuddy 接口地址填写：

```text
https://gbapi.818sx.com/v1
```

## 7. 常见问题

### WorkBuddy 开启工具调用时报 `additionalProperties` 或 `strict`

说明部署的不是本修复版，或者 Render 还没有重新部署最新代码。重新部署 Web Service 后再测。

### WorkBuddy 能调用工具，但最终不回答

通常是流式工具调用收尾格式不符合客户端预期。本修复版已经把工具调用时的 `finish_reason` 调整为 `tool_calls`。

### 图片输入报错

确认 WorkBuddy 发送的是 OpenAI 兼容格式。本修复版支持 `image_url` 和 `input_image` 两类字段。

### Render 部署成功但接口 401

检查 WorkBuddy 的 API Key 是否在 `ALLOWED_TOKENS` 中，并确认请求头是：

```text
Authorization: Bearer 你的 token
```

