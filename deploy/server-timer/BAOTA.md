# 宝塔面板部署：每 3–5 分钟触发全包检测

编排使用滚动预构建镜像 `ghcr.io/leexiexie/scoop-upstream-timer:latest`。传输修复版 `1.0.2` 在本仓库 **Publish Server Image** 工作流发布成功后可用，同时更新 `latest`，保留完整源码提交的 `sha-<提交哈希>` 标签，旧 `1.0.0` / `1.0.1` 标签不被本次发布覆盖。目标平台为 Linux amd64 / arm64。每次升级需拉取镜像并重建容器，`latest` 不会自动替换已运行的容器。不需要下载脚本、创建挂载文件、本地构建或创建 `.env`。发布镜像不代表已在你的宝塔服务器安装或升级。

## 创建编排

1. 进入宝塔 **Docker → 容器编排 → 添加/创建编排**，名称填 `scoop-upstream-timer`。
2. 粘贴 [`compose.baota.yml`](compose.baota.yml) 的完整内容。
3. 直接在宝塔编排的 `environment` 中替换占位值，保留引号：

   ```yaml
   environment:
     GH_TOKEN: "在这里填写你的GitHubToken"
     PYTHONUNBUFFERED: "1"
     PYTHONDONTWRITEBYTECODE: "1"
   ```

4. 点击创建/部署，拉取镜像并启动。无需端口映射、域名或额外文件。

Token 使用 fine-grained PAT，仅授权 `LeeXieXie/scoop-personal`，仓库权限 **Actions: Read and write**，Metadata 读取权限自动包含。Token 是运行时环境变量，不放进镜像。**环境变量对宝塔管理员、Docker 管理员及 `docker inspect` 可见**，不是加密保管。不要截图、发送或提交包含真实 Token 的编排。

## 间隔与参数修改

默认每 3 分钟（180 秒）触发一次：

```yaml
command: ["--interval", "180"]
```

要改成每 5 分钟，将 `180` 改为 `300`。镜像 ENTRYPOINT 已包含 Python 脚本，不要在 command 中重复添加 Python 或脚本路径。修改参数或 Token 后，使用宝塔的**重新部署/重建容器**应用配置，仅重启旧容器不会更新环境变量和启动参数。只保留一个调度器。

## 从旧版本升级

从 `1.0.0` 或 `1.0.1` 升级时，可把 `image` 改为 `ghcr.io/leexiexie/scoop-upstream-timer:1.0.2` 固定本次修复版，或保留 `ghcr.io/leexiexie/scoop-upstream-timer:latest` 跟随滚动发布。旧编排显式 `command: ["--interval", "300"]` 会覆盖新镜像的默认间隔，需要默认 3 分钟时把 `command` 改为 `["--interval", "180"]`。保留服务器上已有的 Token 环境变量，不需要重新生成 Token。等待新镜像发布成功后，在宝塔强制拉取镜像并重新部署/重建容器，**仅重启旧容器不足以升级镜像、环境变量或参数**。命令行等效操作（在保存编排的目录执行，编排文件名不是默认名称时加 `-f 文件名`）：

```sh
docker compose pull scheduler
docker compose up -d --force-recreate scheduler
```

不要将包含真实 Token 的编排复制到聊天或提交到仓库。升级后检查日志中的 `interval_seconds` 为 `180`，并观察两次自然周期。

## 1.0.2 传输修复边界

GET 请求协商 gzip 压缩，也兼容未压缩响应；线上接收数据和解压后的 JSON 分别限制为 4 MiB。解析前检测 Content-Length 不完整响应及损坏/截断的 gzip，临时传输或 JSON 解析失败使用有界 GET 重试，持续失败则跳过触发。诊断仅包含安全的数字或白名单元数据，不记录响应正文、Token 或任意远端响应头/错误文本。

默认 180 秒间隔、最近 100 次工作流运行的排队检查保持不变。派发 POST 仍不自动重试，以免响应丢失后重复触发。该修复不是网络永不失败或更新恰好一次的保证；云端验证通过也不能代替宝塔升级及自然周期验收。

## 确认运行

在宝塔查看 `scoop-upstream-timer` 容器日志：

- `interval_seconds`：默认应为 `180`，选择 5 分钟时为 `300`。
- `dispatched`：GitHub 已接受触发请求，不等于软件已更新成功。
- `busy`：已有未完成检测，跳过重复触发，属于正常情况。
- `cycle_failed`：检查网络、Token 权限/有效期及 GitHub 限流。

再到仓库 **Actions → Upstream Watch** 查看逐包结果，发现新版时检查 Excavator 和后续 CI。没有新版时不启动 Excavator 是正常行为。首次启动立即检查，后续按间隔运行，网络中断、排队或已有任务未完成时不能保证每 3–5 分钟完成更新。5 分钟最多约 288 次触发请求/日，3 分钟约 480 次，可能增加 Actions 使用量，默认使用 3 分钟，如需降低使用量可选 5 分钟。

## 新增包与切换

服务器镜像只负责定时唤醒 GitHub 工作流。上游检测会**动态扫描 `bucket/*.json`**，新增使用受支持 `checkver`/`autoupdate` 格式的清单，无需重新构建 timer 镜像。未知或不受支持的格式应显式报错，不应静默跳过或声称检测成功。

确认两次自然周期和 GitHub 检测结果正常后，再停用旧 Windows 计划任务或其他服务器调度器，保留 GitHub cron 兜底。需要停用时，在宝塔停止此编排。更新 timer 程序时使用发布方提供的新镜像版本并重新部署，不再下载或覆盖服务器脚本。
