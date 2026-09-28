# Nova API 公网部署说明（非 Docker）

本文仅部署现有 `nova_api` FastAPI 包装层；不修改 Nova Core、Gate 逻辑、API 协议或腾讯云 Tool Contract。

## 服务器前置条件

- 一台具有公网 IP 的 Linux 腾讯云轻量应用服务器或 CVM（建议 Ubuntu LTS）。
- 一个已解析到该服务器公网 IP 的域名。
- 域名的 80/443 端口可从互联网访问；API 进程的 8000 端口仅允许本机访问。
- Python 3.10 或更高版本、Nginx 或 Caddy，以及可用于签发 HTTPS 证书的域名。

## 安装与启动

以下命令在项目根目录执行；请将 `<APP_DIR>` 换成实际目录。不要把密钥写入仓库、脚本或反向代理配置。

```sh
cd <APP_DIR>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-prod.txt
chmod 700 start_api.sh

# 仅在当前 shell 演示；生产环境应由 systemd 的 EnvironmentFile 提供。
export NOVA_API_KEY='replace-with-a-long-random-secret'
./start_api.sh
```

启动脚本会设置 `PYTHONPATH=<APP_DIR>/code`，随后执行既有命令：

```sh
python -m nova_api --host 0.0.0.0 --port 8000
```

可选环境变量：

- `NOVA_API_KEY`：必填，用于 `X-Nova-API-Key` 验证。
- `NOVA_API_ARTIFACT_ROOT`：可选，诊断运行结果目录；默认在项目的 `artifacts/nova_api_v0_1/runs`。
- `NOVA_API_HOST`：默认 `0.0.0.0`。
- `NOVA_API_PORT`：默认 `8000`。
- `PYTHON_BIN`：可选，默认 `<APP_DIR>/.venv/bin/python`。

## systemd 服务

创建 `/etc/nova-api.env`，权限设为 `600`、属主 `root`，只包含：

```ini
NOVA_API_KEY=replace-with-a-long-random-secret
NOVA_API_ARTIFACT_ROOT=/opt/nova-api/artifacts/nova_api_v0_1/runs
```

创建 `/etc/systemd/system/nova-api.service`：

```ini
[Unit]
Description=Nova API
After=network.target

[Service]
Type=simple
User=nova
Group=nova
WorkingDirectory=/opt/nova-api
EnvironmentFile=/etc/nova-api.env
ExecStart=/opt/nova-api/start_api.sh
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

执行 `sudo systemctl daemon-reload`、`sudo systemctl enable --now nova-api`，再以 `sudo systemctl status nova-api` 查看状态。

## HTTPS 反向代理

推荐 Caddy：它会自动申请和续期 HTTPS 证书。`/etc/caddy/Caddyfile` 的最小配置为：

```caddy
api.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

将 `api.example.com` 换为真实域名，并确保 DNS A 记录已指向服务器公网 IP。不要将 `NOVA_API_KEY` 放入 Caddyfile。若使用 Nginx，则将 `127.0.0.1:8000` 作为 upstream，并用已有证书或 Certbot 配置 TLS。

## 上线前验收

```sh
curl -fsS https://api.example.com/health
curl -fsS https://api.example.com/v1/protocol
curl -fsS -X POST https://api.example.com/v1/diagnosis/run \
  -H 'Content-Type: application/json' \
  -H 'X-Nova-API-Key: <NOVA_API_KEY>' \
  -d '{"input_type":"demo_case","case_id":"CASE-DEMO-002"}'
```

最后一条应返回 HTTP 200，并包含 `run_id`、`experiments`、`key_evidence`、`traceability`，且 `gate.decision` 为 `BLOCKED`。

## 腾讯云 Tool 参数

- Base URL：`https://<真实域名>`
- Method：`POST`
- Path：`/v1/diagnosis/run`
- Header：`X-Nova-API-Key: <生产环境密钥>`、`Content-Type: application/json`
- 首轮 Body：`{"input_type":"demo_case","case_id":"CASE-DEMO-002"}`
- 映射字段：`run_id`、`gate.decision`、`gate.reason`、`experiments`、`key_evidence`、`traceability`

不要启用 `file_reference`：当前 API 对该输入明确返回 `FILE_REFERENCE_ADAPTER_PENDING_TENCENT_INTEGRATION`。
