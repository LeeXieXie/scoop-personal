# 宝塔面板部署：每 3–5 分钟触发全包检测

默认 **5 分钟（300 秒）**，希望更快可改成 **3 分钟（180 秒）**。
服务器只负责定时唤醒 GitHub 上的 `Upstream Watch`，仍由它检查桶中全部包并按需启动 Excavator。
不需要安装 gh、不需要本地构建镜像、不需要域名或放行端口。

> 下面是交付的部署步骤，不表示已经连接或安装到你的服务器。
> 宝塔界面名称可能因版本略有不同。[官方容器编排说明](https://docs.bt.cn/user-guide/docker/compose/)和[官方教程](https://www.bt.cn/bbs/thread-140412-1-1.html)支持直接粘贴 Compose 文件创建编排。

## 1. 准备服务器目录与两个文件

在宝塔的「文件」中创建目录，或在服务器终端执行：

```sh
sudo install -d -m 755 /www/server/scoop-upstream-timer
```

通过宝塔文件管理器将下面两个文件放在该目录中：

```text
/www/server/scoop-upstream-timer/
├── server_upstream_timer.py
└── github-token
```

- `server_upstream_timer.py`：从本仓库 [`scripts/server_upstream_timer.py`](../../scripts/server_upstream_timer.py) 下载，保留这个文件名。请下载更新后的版本，旧版默认间隔为 30 分钟。
- `github-token`：在**服务器上**新建普通文本文件，只写入你的 GitHub Token，不加引号，不写 `GH_TOKEN=`，不要使用 UTF-8 BOM。

Token 应为 fine-grained PAT，仅允许 `LeeXieXie/scoop-personal`，仓库权限 **Actions: Read and write**。Metadata 的读取权限会自动包含。不需要给其他仓库授权，也不要把 Token 发到聊天、Git 或截图里。

服务器终端设置权限：

```sh
sudo chmod 644 /www/server/scoop-upstream-timer/server_upstream_timer.py
sudo chown 10001:10001 /www/server/scoop-upstream-timer/github-token
sudo chmod 600 /www/server/scoop-upstream-timer/github-token
```

容器使用 UID/GID `10001:10001`，所以 Token 必须可被这个 UID 读取。不要为了修复权限把 Token 改成 777 或所有人可读。可以将目录放在其他位置，但必须同步修改下面编排中的两个 `source`。

## 2. 在宝塔创建容器编排

1. 进入宝塔 **Docker → 容器编排 → 添加/创建编排**。
2. 编排名可填 `scoop-upstream-timer`。
3. 选择「Compose 内容」或类似的直接编辑方式。
4. 粘贴 [`compose.baota.yml`](compose.baota.yml) 的**完整内容**。
5. 保留 `--interval`, `300`，即默认 5 分钟；改为 `180` 就是 3 分钟。
6. 创建/部署，等待拉取官方 `python:3.13-slim` 镜像并启动容器。

不需要填写端口映射。此程序没有网页管理界面，「访问」按钮不可用是正常现象。镜像拉取失败时应先解决服务器的 Docker Hub 连接，不要把自己的 GitHub Token 填到镜像仓库密码里。

编排使用绝对文件路径，不依赖宝塔把编排保存在哪个目录。两个文件必须**提前存在且是普通文件**；配置中的 `create_host_path: false` 可避免错误路径被自动创建成目录。较旧 Compose 如果不支持这个选项，优先升级宝塔 Docker 模块或 Compose，而不是直接去掉文件检查后盲目启动。

## 3. 看日志确认运行

在宝塔打开该编排下 `scoop-upstream-timer` 容器的日志。正常情况会出现 JSON 记录：

- 启动配置记录中的 `interval_seconds` 为 `300` 或 `180`。
- `dispatched`：GitHub 接受了本次触发请求。
- `busy`：已有未完成的上游检测，跳过重复触发，属于正常情况。
- `cycle_failed`：网络、权限、限流等错误，按记录排查。Token 过期或授权错误必须在服务器上修正。

`dispatched` 不等于软件已经更新成功。打开仓库 **Actions → Upstream Watch**，确认全部包检测结果；发现新版时再看 Excavator 和后续 CI 是否成功。没有新版时不启动 Excavator 是正确行为。

首次启动会立即检查，之后以 300 秒或 180 秒的启动节拍运行。请求耗时会占用周期，超过周期时跳过错过的时刻，不连续补发请求。网络中断、GitHub 排队、已有运行未完成时，不能保证每 3–5 分钟完成一次更新。

正常 5 分钟计划最多约 288 次触发请求/日，3 分钟最多约 480 次；已有任务会去重跳过。每次都需要 Linux 检测任务，可能增加 Actions 使用量。建议先用 5 分钟。

## 4. 改为 3 分钟或回到 5 分钟

在宝塔编辑编排，只改命令最后的数字，然后重新部署/重建容器：

```yaml
command: ["python", "/app/server_upstream_timer.py", "--interval", "180"]
```

- 3 分钟：`180`
- 5 分钟：`300`

只点「重启」不一定应用变更后的编排配置，应使用面板的重新部署/更新编排。不要创建第二个同名或不同名的调度器来代替修改。

## 5. 成功后切换与回滚

在服务器上观察**两次自然周期**，核对 GitHub 运行创建时间和逐包检测结果。完成后：

- 只保留这一套服务器编排，停用同机另装的 systemd timer 或另一个 Docker 调度器。
- 在原 Windows 电脑上执行 `Disable-ScheduledTask -TaskName ScoopPersonalUpstreamWatch`，停掉旧的半小时触发器。服务器未验收前先不要停。
- 保留仓库原 GitHub cron 作低可靠性兜底。

需要停用服务器任务时，在宝塔停止该编排即可。不要删除 Token 文件，除非你确实要撤销部署。回滚可停止服务器编排，然后恢复 Windows 任务：`Enable-ScheduledTask -TaskName ScoopPersonalUpstreamWatch`。

更新程序时，先备份旧脚本，用新文件覆盖 `server_upstream_timer.py`，保持文件名与权限不变，再重建/重启容器。Token 文件始终只保存在服务器，不放进镜像。
