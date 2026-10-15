# Scoop Personal

[![CI](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml) [![Excavator](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml)

这是用于维护仓库所有者关注的 Windows 应用的个人 [Scoop](https://scoop.sh) 软件桶，不是 [Extras](https://github.com/ScoopInstaller/Extras) 的 fork 或镜像。**当前已收录 `magpie-ai`、`magpie-ai-cli`、`opencode2` 和 `openchamber`。**

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

可通过[软件收录申请](https://github.com/LeeXieXie/scoop-personal/issues/new?template=package-request.yml)记录想收录的应用；申请只用于跟踪，不会自动转换为清单，也不保证收录。

## 自动更新

- Upstream Watch 按 UTC cron `2-57/5 * * * *` 每 5 分钟在 Linux runner 上检查官方最新稳定版；任一 Magpie 清单版本不一致，且 GUI、CLI 的 x64/ARM64 文件及 `SHA256SUMS` 全部上传完成后，才触发现有 Excavator。文件未齐时等待下一次检查；检查时发现 Excavator 已在运行/排队则跳过，无新版本时不启动 Excavator。检查与触发之间若恰逢手动或定时启动 Excavator，可能重复排队；已有并发锁保证串行执行。
- Excavator 按 UTC cron `17 * * * *` 每小时运行一次（北京时间每小时第 17 分），也可在 Actions 中通过 `workflow_dispatch` 手动运行；手动运行请选择 `master` 分支。`opencode2` 与 `openchamber` 只能等这个定时任务发现新版本，最长延迟约 1 小时。
- `magpie-ai` 与 `magpie-ai-cli` 不受上面间隔影响：Upstream Watch 仍每 5 分钟检查一次，发现新版本且官方文件齐全时立即派发 Excavator，所以 Magpie 的更新仍可在数分钟内合入。若希望监听任务也降频，请一并修改 `upstream-watch.yml` 的 cron。
- GitHub 定时任务可能排队或延迟，实际运行间隔及更新完成时间可能长于上面设定的 cron 周期。
- 真实清单须同时正确配置 `checkver` 与 `autoupdate` 才能参与自动更新。工作流检查新版本、下载文件并计算及检查哈希，将清单更新提交到 `master`。
- `magpie-ai` 与 `magpie-ai-cli` 均通过 Upstream Watch 和 Excavator 跟踪官方最新稳定版，使用官方发布的 `SHA256SUMS` 获取校验值，不依赖 Main/Extras 清单的更新时间。工作流只更新桶内清单，不会自动更新用户本地已安装的应用；本地更新仍需执行 `scoop update`。
- `opencode2` 与 `openchamber` 只依赖定时 Excavator 的通用机制：按各自 `checkver` 发现新版本，再按 `autoupdate` 重写 URL、按 `hash.url` 抓取校验值。前者从 npm registry 的 `dist.integrity` 取 SHA-512，后者从官方 `latest.yml` / `latest-arm64.yml` 取 SHA-512，均不使用 Upstream Watch。上游发布不完整时清单可能失败，必要时人工修正。
- Upstream Watch 使用标准 `GITHUB_TOKEN` 的 `contents: read` 和 `actions: write` 权限调用已有 `workflow_dispatch`，无需额外配置 PAT；可手动在 `master` 分支运行监听任务。
- `magpie-ai` 安装 `magpie.exe` 并持久化 `data` 目录。
- `magpie-ai` 首次初始化时，仅在不存在已持久化的 `settings.json` 时设置 `noAutoUpdate = true`，关闭应用自更新，由 Scoop 负责更新；不会覆盖已持久化的设置。
- `THROW_ERROR: 1` 会将检查失败作为错误报告。同一分支的 Excavator 更新任务互斥执行，不取消正在运行的任务。
- 标准 `GITHUB_TOKEN` 的机器人提交不会触发 `push` CI。手动与定时 Excavator 成功后，通过 `workflow_run` 接续测试；监听工作流派发的机器人 Excavator 成功后，显式派发 `workflow_dispatch` 触发 CI。Excavator 失败时不会启动测试。
- 公开仓库连续 60 天无活动时，GitHub 可能禁用定时工作流；需要时到 Actions 中重新启用。

## 参考与许可

清单编写参见 [App Manifests](https://github.com/ScoopInstaller/Scoop/wiki/App-Manifests)，自动更新规则参见 [Autoupdate](https://github.com/ScoopInstaller/Scoop/wiki/Autoupdate)。

本仓库由[官方 BucketTemplate](https://github.com/ScoopInstaller/BucketTemplate) 生成，模板采用 [Unlicense](LICENSE)。原始清单模板与 LICENSE 保持不变；应用本身遵循各自的许可证。
