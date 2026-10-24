# Scoop Personal

[![CI](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml) [![Excavator](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml)

这是用于维护仓库所有者关注的 Windows 应用的个人 [Scoop](https://scoop.sh) 软件桶，不是 [Extras](https://github.com/ScoopInstaller/Extras) 的 fork 或镜像。**当前已收录 `magpie-ai`、`magpie-ai-cli`、`opencode2`、`openchamber`、`zcode`、`smartsearch`、`jcode` 和 `pebrel`。**

## 使用

先安装 Scoop；`personal` 可与 `extras` 并存：

```powershell
scoop bucket add personal https://github.com/LeeXieXie/scoop-personal
scoop bucket add extras
```

首次安装 `magpie-ai`，并在后续更新时使用（已从 Extras 安装的用户请先阅读下方提示）：

```powershell
scoop install personal/magpie-ai
scoop update magpie-ai
```

若已从 Extras 安装 `magpie-ai`，请勿重复安装同名包。先运行 `scoop info magpie-ai` 核对来源并备份配置；切换清单来源前，请先核实能保留现有应用与 `persist` 数据的操作方式。

CLI 可单独安装，无需先安装 GUI。首次安装 `magpie-ai-cli`、查看命令帮助及后续更新（已从 Main 安装的用户请先阅读下方提示）：

```powershell
scoop install personal/magpie-ai-cli
magpie-cli --help
scoop update magpie-ai-cli
```

若已从 Main 安装 `magpie-ai-cli`，仅添加 `personal` 桶不会切换已安装包的来源，请勿重复安装同名包。迁移前请先运行 `scoop info magpie-ai-cli` 核对来源、备份配置，并核实能保留现有应用与数据的操作方式。

`opencode2` 的 v2 配置与 v1 不兼容，请先卸载 `main/opencode` 再安装；`openchamber` 若已从 `extras` 安装，请勿重复安装同名包。安装与后续更新：

```powershell
scoop install personal/opencode2
scoop install personal/openchamber
scoop update opencode2 openchamber
```

安装前请检查清单及其调用的安装脚本，尤其是自动更新后的变更。

ZCode 社区构建（Windows x64）：

```powershell
scoop install personal/zcode
scoop update zcode
```

该包直接解压安装器，不运行 NSIS 安装程序、不注册系统协议、不修改已有用户数据。开始菜单入口为 `ZCode (Community)`，不创建可能与其他 ZCode CLI 冲突的 `zcode` 命令。若已安装官方版，请勿同时运行两个共享默认数据目录的实例。

Smart Search 桌面版与 Jcode（均支持 Windows x64 / ARM64）：

```powershell
scoop install personal/smartsearch
scoop install personal/jcode
jcode --version
scoop update smartsearch jcode
```

`smartsearch` 是图形桌面管理器，不会替换已有 npm 版 `smart-search` 命令；独立搜索 CLI 可保留现有安装，或通过应用设置页配置。`jcode` 创建同名终端命令，模型认证需另行配置；若已有其他渠道安装的 Jcode，请先核对命令来源。

安装 Pebrel 终端及后续更新：

```powershell
scoop install personal/pebrel
scoop update pebrel
```

## 已收录应用

[`magpie-ai`](bucket/magpie-ai.json)：[Magpie 官方主页](https://usemagpie.ai) · [官方发布仓库](https://github.com/yetone/magpie-releases)。支持 Windows x64 和 ARM64；首次收录版本为 `0.1.1104`，当前版本以清单为准。

清单参考 [ScoopInstaller/Extras 的 magpie-ai.json](https://github.com/ScoopInstaller/Extras/blob/master/bucket/magpie-ai.json)，参考清单采用 Unlicense；软件官方源码 [yetone/magpie](https://github.com/yetone/magpie) 采用 MIT 许可证。本桶通过现有 Excavator 直接跟踪官方 `yetone/magpie-releases` 的最新稳定版，不会定时同步 Extras 的完整清单；上游安装逻辑的变更需人工审核后合入。

Scoop 自 `0.1.1067` 起持久化 Magpie 数据。旧配置位于 `$env:USERPROFILE\.config\magpie`，当前持久化目录为 `$persist_dir\data`。如需沿用旧配置，请先备份并自行迁移；清单不会自动迁移旧数据。

[`magpie-ai-cli`](bucket/magpie-ai-cli.json)：[Magpie 官方发布仓库](https://github.com/yetone/magpie-releases)。支持 Windows x64 和 ARM64；首次收录版本为 `0.1.1104`，当前版本以清单为准。可执行文件为 `magpie-cli.exe`，Scoop shim 命令为 `magpie-cli`；可与 `magpie-ai` 并存，不会覆盖 GUI 的 `magpie.exe`。

清单参考 [ScoopInstaller/Main 的 magpie-ai-cli.json](https://github.com/ScoopInstaller/Main/blob/master/bucket/magpie-ai-cli.json)，参考清单采用 Unlicense；应用采用 MIT 许可证。CLI 不应用 GUI 的 `persist` 钩子或 `noAutoUpdate` 设置。

[`opencode2`](bucket/opencode2.json)：[OpenCode 官方主页](https://opencode.ai/v2) · [npm 发布包](https://www.npmjs.com/package/@opencode/cli)。OpenCode v2 CLI，下载源为官方 npm 平台包 `@opencode/cli-windows-x64` / `@opencode/cli-windows-arm64`；支持 Windows x64 和 ARM64；首次收录版本为 `2.0.29`，当前版本以清单为准。同时创建 `opencode` 和 `opencode2` 两个命令；v2 配置与 v1 不兼容，安装前请先卸载 `opencode`，迁移步骤见[官方文档](https://opencode.ai/v2/docs/migrate-v1/)。

清单参考 [ScoopInstaller/Versions 的 opencode2.json](https://github.com/ScoopInstaller/Versions/blob/master/bucket/opencode2.json)（注意：上游清单在 `Versions` 桶而非 `Extras`），参考清单采用 Unlicense；应用采用 MIT 许可证。校验值来自 npm registry 的 `dist.integrity`（SHA-512）。

[`openchamber`](bucket/openchamber.json)：[OpenChamber 官方主页](https://openchamber.dev) · [官方发布仓库](https://github.com/openchamber/openchamber)。基于 OpenCode AI agent 的 Agentic Development Environment（GUI），支持 Windows x64 和 ARM64；首次收录版本为 `2.3.3`，当前版本以清单为准。

清单参考 [ScoopInstaller/Extras 的 openchamber.json](https://github.com/ScoopInstaller/Extras/blob/master/bucket/openchamber.json)，参考清单采用 Unlicense；应用采用 MIT 许可证。安装脚本解包 Electron 安装器内 `$PLUGINSDIR` 的 `app-*.7z` 并删除安装器残留；校验值与官方 `latest.yml` / `latest-arm64.yml` 中的 SHA-512 一致。

[`zcode`](bucket/zcode.json)：[社区构建仓库](https://github.com/LeeXieXie/zcode-releases) · [上游源码](https://github.com/zai-org/ZCode)。仅支持 Windows x64；Scoop 版本采用“应用版本.UTC 源码提交时间-upstream.SHA”，确保相同应用版本下的新提交按时间更新，而不是错误地按随机 SHA 排序。下载社区 Release 的 EXE，解包内层 `app-64.7z`；校验值来自同一 Release 的 `SHA256SUMS.txt`。版本信息读取公开 Release 的 `build-provenance.json`，不依赖匿名 GitHub API 配额；由全包 Upstream Watch 检查更新，并由每 30 分钟一次的 Excavator 兜底，无需单独的 ZCode 工作流。

这是非官方、未签名构建，Computer Use 不可用；其他功能的资源完整性检查不等于端到端功能验证。上游仍有第三方许可材料缺口，请先阅读 Release 附带声明。自动更新已在构建中关闭，更新由 Scoop 管理；不迁移或删除上游默认位置的用户数据。

[`smartsearch`](bucket/smartsearch.json)：[上游项目及发布页](https://github.com/konbakuyomu/smartsearch)。首次收录版本为 `0.1.31`，支持 Windows 10 2004（build 19041）及以上系统、x64 和 ARM64。下载官方 Velopack **完整包**，直接解压 `lib/app`，不运行 Setup、不使用增量包；开始菜单入口为 `Smart Search`，明确指定随包图标。该桌面包自包含 .NET 运行时，但不包含独立 `smart-search` CLI；提供商 API Key、技能和 CLI 路径需在应用中配置。散包未注册为 Velopack 安装，应用内自动更新不接管此安装；使用 Scoop 更新。清单不移动或删除用户配置。

[`jcode`](bucket/jcode.json)：[上游项目及发布页](https://github.com/1jehuang/jcode)。首次收录版本为 `0.99.1`，支持 Windows x64 和 ARM64。下载官方压缩包，以 `jcode` shim 指向对应架构的原生 EXE，不运行上游安装器、不额外生成另一套启动器。配置保留在上游默认 `~/.jcode` 或用户指定的 `JCODE_HOME`；安装时设置 `JCODE_NO_AUTO_UPDATE=1` 禁用自动自更新检查。请使用 `scoop update jcode` 而非 `jcode update`，避免绕过 Scoop 版本管理。模型服务、凭据及权限不包含在此软件包中。

[`jcode-desktop`](bucket/jcode-desktop.json)：[官方项目与发布页](https://github.com/1jehuang/jcode-desktop)。首次收录 `0.6.5`，现按用户要求跟踪最新发布，**包括 beta、RC 等测试/预发布版本**，当前为 `0.6.6-beta.1`。支持 Windows x64 / ARM64；直接解压官方 ZIP，自带 Jcode 后端和 API Bridge，不依赖独立 `jcode` 包，也不覆盖其终端命令。开始菜单入口为 `Jcode Desktop`，使用随包 PNG 生成的 ICO；运行中任务栏图标不在此保证范围。配置默认与 CLI 共用 `~/.jcode/config.toml`，桌面状态默认位于 `%LOCALAPPDATA%/Jcode Desktop`，清单不迁移这些数据。

```powershell
scoop install personal/jcode-desktop
scoop update jcode-desktop
```

注意：该版本桌面内置更新在启动后和每 4 小时检查并原地替换便携文件，未发现关闭开关。因此实际文件版本可能领先 Scoop 记录，不能声称由 Scoop 独占更新。校验值分别读取 `SHA256SUMS-windows` 和 `SHA256SUMS-windows-aarch64`，不使用只含其他平台的根校验文件。参与全包 Upstream Watch，并沿用每 30 分钟一次的 Excavator 兜底；CI 验证两个架构的下载、Scoop 解压、三份 EXE 架构与快捷方式图标生成，不启动桌面程序。

版本检测读取公开 `releases.atom` 的首个版本条目，而不是排除测试版的 `/releases/latest`；保留完整测试版后缀用于版本比较、下载和解压目录。测试版本可能不稳定，更新前请备份重要配置与会话。此规则仅用于 `jcode-desktop`，不改变其他软件包的稳定版策略。

[`pebrel`](bucket/pebrel.json)：[官方源码与发布仓库](https://github.com/Kuddev/pebrel)。GPU 加速终端、SSH 工作区与 AI CLI 会话管理工具，采用官方 Windows x64 / ARM64 便携 ZIP；首次收录版本为 `2.2.2`，当前版本以清单为准。提供 `pebrel` 命令和 Pebrel 开始菜单快捷方式，应用采用 GPL-3.0 许可证。

配置保存在 `%APPDATA%\Pebrel`，不位于 Scoop 安装目录，无需额外的 `persist` 或自动迁移脚本。上游首次启动会配置 AI CLI 通知集成，可通过 `pebrel setup-ai --remove` 撤销。请使用 Scoop 更新，避免使用应用内更新安装器。清单通过 GitHub 最新稳定版检测更新，并从官方 `SHA256SUMS` 获取两个架构的 SHA-256 校验值，参与全包 Upstream Watch，并由每 30 分钟一次的 Excavator 任务兜底。

## 维护与添加应用

维护者工作副本应为 `https://github.com/LeeXieXie/scoop-personal.git` 的克隆，使用默认分支 `master`。以下本地命令均在该副本的仓库根目录运行。

1. 将 `bucket/app-name.json.template` 复制为 `bucket/<app-name>.json`；应用名使用小写字母、数字和连字符。
2. 根据官方资料填写 `version`、`description`、`homepage`、`license`，为实际支持的架构填写下载 URL 和真实校验值（`hash`），删除不适用的字段。`hash` 默认按 SHA256 解析，其他算法需显式加前缀，例如 `sha512:<hex>`；上游清单已用 SHA-512/MD5 时照抄其算法即可。
3. 依据真实的官方发布源配置 `checkver` 和 `autoupdate`；不能假设任意应用都能自动更新。需要保留的用户数据使用 `persist`，按需配置 `shortcuts`。
4. 执行本地检查，审核清单变更与安装脚本后，再提交到 `master`。

已下载到本地的文件可这样计算校验值（文件名仅为示例）：

```powershell
Get-FileHash .\downloaded-installer.exe -Algorithm SHA256
Get-FileHash .\downloaded-installer.exe -Algorithm SHA512
```

官方发布页直接提供校验值时优先采用其值，并注意格式换算。Electron 安装器的 `latest.yml` 给出 Base64 编码的 SHA-512，npm registry 的 `dist.integrity` 形如 `sha512-<base64>`，两者都要转成十六进制再写入 `hash`：

```powershell
-join ([Convert]::FromBase64String('PobsacJ/bt4CHMUADEDrQSWdT3WM88ipTYHMDlOEnK1OIZWeyPiCGYl3aOadbBA1JTuvr1K1qG9nl1k6yOpQ0A==') | ForEach-Object ToString x2)
```

本地测试需要已安装的 Scoop、BuildHelpers >= 2.0.1 和 Pester >= 5.2.0。将下面的 `<app-name>` 替换为清单名（不含 `.json`）；`-Update` 会修改清单：

```powershell
.\bin\formatjson.ps1 <app-name>
.\bin\checkurls.ps1 <app-name>
.\bin\checkhashes.ps1 <app-name>
.\bin\checkver.ps1 <app-name>
.\bin\checkver.ps1 <app-name> -Update
.\bin\test.ps1
```

GitHub CI 会检出 Scoop，安装并缓存测试依赖，分别在 `powershell` 和 `pwsh` 下运行测试。

全包上游监听使用 Python 标准库，可在仓库根目录运行离线回归与真实只读检查；默认不会修改清单或派发更新：

```powershell
python -m unittest discover -s scripts -p "test_upstream_watch.py"
python scripts/upstream_watch.py
```

`smartsearch` 或 `jcode` 清单发生变化时，PowerShell 7 CI 还会下载两个架构的实际发布包，核对随 Release 发布的 SHA256、使用 Scoop 解压函数验证文件布局、检查 EXE 架构；Jcode x64 额外在隔离配置目录中执行 `--version`。这不替代桌面完整功能或模型会话验证。

可通过[软件收录申请](https://github.com/LeeXieXie/scoop-personal/issues/new?template=package-request.yml)记录想收录的应用；申请只用于跟踪，不会自动转换为清单，也不保证收录。

## 自动更新

- Upstream Watch 配置为按 UTC cron `2-57/5 * * * *` 每 5 分钟在 Linux runner 上检查 `bucket/*.json` 中的全部软件包，目前共 9 个，不再只检查 Magpie。检测规则来自各清单的 `checkver` 和 `autoupdate`，不另存一份版本号；GitHub 包按各自发布源检查，`opencode2` 查询 npm，`jcode-desktop` 保留 Atom 首条发布含测试版的规则，`zcode` 从构建 provenance 生成带 UTC 时间戳的版本。
- Excavator 按 UTC cron `17,47 * * * *` 配置为每 30 分钟运行一次（北京时间每小时第 17、47 分），避开整点高峰；也可在 Actions 中通过 `workflow_dispatch` 手动运行，手动运行请选择 `master` 分支。`opencode2`、`openchamber`、`zcode`、`smartsearch`、`jcode`、`jcode-desktop` 与 `pebrel` 均由这个定时任务检查各自上游的新版本。
- 监听仅在上游版本更新且清单要求的各架构下载包、校验文件等产物就绪时派发；Magpie 继续要求 GUI、CLI 两个架构共四份 EXE 与 `SHA256SUMS` 全部上传完成。监听只检查发布元数据，不代替 Excavator 的实际下载和哈希校验。单包检测失败不阻止其他包继续检查，有就绪更新仍可派发，但失败会记录并令监听任务报错；未知规则也会显式报错，不能静默漏包。新增清单使用监听器尚不支持的 `checkver` 时需补适配，ZCode 的特殊脚本规则变动需同步审核适配快照。
- 全部包均参与上游监听，不再将非 Magpie 软件限制为仅靠半小时定时检查。监听会逐包报告当前版本、上游版本与检测结果；无新版本时不启动 Excavator。检查时发现 Excavator 已在运行/排队则跳过；检查与触发之间若恰逢其他入口启动 Excavator，仍可能重复排队，已有并发锁保证串行执行。
- GitHub 定时任务可能排队、延迟或丢弃，实际运行间隔及更新完成时间可能长于上面设定的 cron 周期；30 分钟和 5 分钟均为计划检查频率，不保证准点触发或在该时间内完成更新。上游发布后即时触发需要上游工作流或 webhook 主动向本仓库派发事件，仅在本仓库添加 `release` 触发器无法监听其他仓库的发布。
- 真实清单须同时正确配置 `checkver` 与 `autoupdate` 才能参与自动更新。工作流检查新版本、下载文件并计算及检查哈希，将清单更新提交到 `master`。
- `magpie-ai` 与 `magpie-ai-cli` 均通过 Upstream Watch 和 Excavator 跟踪官方最新稳定版，使用官方发布的 `SHA256SUMS` 获取校验值，不依赖 Main/Extras 清单的更新时间。工作流只更新桶内清单，不会自动更新用户本地已安装的应用；本地更新仍需执行 `scoop update`。
- `pebrel` 同时参与 Upstream Watch 与定时 Excavator，使用官方便携 ZIP 和 `SHA256SUMS`。
- `opencode2` 与 `openchamber` 同时参与 Upstream Watch 与定时 Excavator：监听发现新版本后派发更新，Excavator 再按各自 `checkver` / `autoupdate` 重写 URL、按 `hash.url` 抓取校验值。前者从 npm registry 的 `dist.integrity` 取 SHA-512，后者从官方 `latest.yml` / `latest-arm64.yml` 取 SHA-512。监听不替代实际下载和哈希校验，上游发布不完整时仍可能失败，必要时人工修正。
- `smartsearch` 与 `jcode` 同时参与 Upstream Watch，并沿用每 30 分钟一次的 Excavator 兜底，分别从官方 Release 的 `SHA256SUMS.txt` / `SHA256SUMS` 读取 SHA256。Smart Search 使用完整 nupkg，Jcode 使用各架构 tar.gz；若任一架构产物未齐或校验失败，不应将其当作可安装的新版本。
- Upstream Watch 使用标准 `GITHUB_TOKEN` 的 `contents: read` 和 `actions: write` 权限调用已有 `workflow_dispatch`，无需额外配置 PAT；可手动在 `master` 分支运行监听任务。
- `magpie-ai` 安装 `magpie.exe` 并持久化 `data` 目录。
- `magpie-ai` 首次初始化时，仅在不存在已持久化的 `settings.json` 时设置 `noAutoUpdate = true`，关闭应用自更新，由 Scoop 负责更新；不会覆盖已持久化的设置。
- `THROW_ERROR: 1` 会将检查失败作为错误报告。同一分支的 Excavator 更新任务互斥执行，不取消正在运行的任务。
- 标准 `GITHUB_TOKEN` 的机器人提交不会触发 `push` CI。手动与定时 Excavator 成功后，通过 `workflow_run` 接续测试；监听工作流派发的机器人 Excavator 成功后，显式派发 `workflow_dispatch` 触发 CI。Excavator 失败时不会启动测试。
- 公开仓库连续 60 天无活动时，GitHub 可能禁用定时工作流；需要时到 Actions 中重新启用。

## 常在线服务器部署

服务器版使用 Python 标准库直接调用 GitHub API，默认每 **5 分钟（300 秒）**唤醒现有全包监听，可用 `--interval 180` 调整为 **3 分钟**；不依赖 Windows 开机或 `gh` 登录，也不开放入站端口。提供 Docker Compose 常驻进程及 Linux systemd timer 两种部署方式，包含超时、有限重试、队列防重与结构化日志。

程序入口为 [`scripts/server_upstream_timer.py`](scripts/server_upstream_timer.py)。**宝塔用户直接看 [中文部署步骤](deploy/server-timer/BAOTA.md)，将 [宝塔编排文件](deploy/server-timer/compose.baota.yml) 粘贴到 Docker → 容器编排，在 `environment` 填入 GitHub Token 后部署即可。使用已发布并通过匿名拉取运行验证的预构建镜像 `ghcr.io/leexiexie/scoop-upstream-timer:1.0.0`，无需下载脚本、创建挂载文件、创建 `.env` 或自行构建镜像。环境变量对宝塔/Docker 管理员及 `docker inspect` 可见，不要截图或提交真实 Token。** 其他安装方式、凭据权限、运行检查及卸载步骤见 [`deploy/server-timer/README.md`](deploy/server-timer/README.md)。凭据只放在服务器环境或私有文件，不提交到仓库。部署文件交付不等于已安装到服务器；服务器上观察两次自然成功运行后，再禁用下面的 Windows 任务，避免多个独立计时器重复唤醒。

## 独立定时触发（Windows 维护者工作站）

GitHub cron 曾在实际观察中超过 90 分钟未触发半小时任务。维护者可用 Windows 任务计划程序独立计时，每 30 分钟调用现有全包 Upstream Watch，原 GitHub cron 继续兜底：

```powershell
.\scripts\windows-upstream-timer.ps1 -Install
Get-ScheduledTaskInfo -TaskName ScoopPersonalUpstreamWatch
# 撤销本机任务，不删除日志或更改 GitHub 工作流：
.\scripts\windows-upstream-timer.ps1 -Uninstall
```

此任务以当前用户、非提权、交互式登录方式运行，不保存登录密码，也不把 GitHub 凭据提交或上传给第三方；调用已安装 GitHub CLI 的现有 keyring 登录。**仅在这台电脑开机、联网且当前用户已登录时有效**，休眠、注销、断网期间不保证运行，恢复后由任务计划程序补启动。仓库路径和 `gh.exe` 路径变更后需重新安装任务。脚本会清除当前进程继承的 `GH_TOKEN` / `GITHUB_TOKEN` 后复用 keyring，避免其他应用的环境 token 干扰。

运行记录位于 `%LOCALAPPDATA%\ScoopPersonalUpstreamWatch\trigger.log`（超过 1 MiB 保留一份前轮日志）。已有未完成的 Watch 会跳过重复派发。成功日志表示 GitHub 接受触发请求，仍需在 Actions 核实逐包检测及更新结果；不能保证 runner 准点完成。如需电脑关机后也持续运行，应将相同 API 调用移至独立常在线的调度服务。

## 参考与许可

清单编写参见 [App Manifests](https://github.com/ScoopInstaller/Scoop/wiki/App-Manifests)，自动更新规则参见 [Autoupdate](https://github.com/ScoopInstaller/Scoop/wiki/Autoupdate)。

本仓库由[官方 BucketTemplate](https://github.com/ScoopInstaller/BucketTemplate) 生成，模板采用 [Unlicense](LICENSE)。原始清单模板与 LICENSE 保持不变；应用本身遵循各自的许可证。
