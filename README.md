# Scoop Personal

[![CI](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/ci.yml) [![Excavator](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml/badge.svg?branch=master)](https://github.com/LeeXieXie/scoop-personal/actions/workflows/excavator.yml)

这是用于维护仓库所有者关注的 Windows 应用的个人 [Scoop](https://scoop.sh) 软件桶，不是 [Extras](https://github.com/ScoopInstaller/Extras) 的 fork 或镜像。**当前 bucket 仅包含清单模板，没有可安装的应用。**

## 使用

先安装 Scoop；`personal` 可与 `extras` 并存：

```powershell
scoop bucket add personal https://github.com/LeeXieXie/scoop-personal
scoop bucket add extras
```

以下仅为安装语法：须先添加并发布对应的真实清单，再用实际应用名替换 `<app-name>`；当前没有可供安装的应用。

```powershell
scoop install personal/<app-name>
```

安装前请检查清单及其调用的安装脚本，尤其是自动更新后的变更。

## 维护与添加应用

维护者工作副本应为 `https://github.com/LeeXieXie/scoop-personal.git` 的克隆，使用默认分支 `master`。以下本地命令均在该副本的仓库根目录运行。

1. 将 `bucket/app-name.json.template` 复制为 `bucket/<app-name>.json`；应用名使用小写字母、数字和连字符。
2. 根据官方资料填写 `version`、`description`、`homepage`、`license`，为实际支持的架构填写下载 URL 和真实 SHA256（`hash`），删除不适用的字段。
3. 依据真实的官方发布源配置 `checkver` 和 `autoupdate`；不能假设任意应用都能自动更新。需要保留的用户数据使用 `persist`，按需配置 `shortcuts`。
4. 执行本地检查，审核清单变更与安装脚本后，再提交到 `master`。

已下载到本地的文件可这样计算 SHA256（文件名仅为示例）：

```powershell
Get-FileHash .\downloaded-installer.exe -Algorithm SHA256
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

- Excavator 按 UTC cron `20 */4 * * *` 每 4 小时运行一次，也可在 Actions 中通过 `workflow_dispatch` 手动运行；手动运行请选择 `master` 分支。
- 真实清单须同时正确配置 `checkver` 与 `autoupdate` 才能参与自动更新。工作流检查新版本、下载文件并计算及检查哈希，将清单更新提交到 `master`。当前没有应用，因此不会执行实际应用更新。
- `THROW_ERROR: 1` 会将检查失败作为错误报告。同一分支的 Excavator 更新任务互斥执行，不取消正在运行的任务。
- 标准 `GITHUB_TOKEN` 的机器人提交不会触发 `push` CI，因此 CI 除推送、PR 和手动触发外，也通过 `workflow_run` 跟随成功完成的 Excavator 运行；Excavator 失败时跳过该测试任务。
- 公开仓库连续 60 天无活动时，GitHub 可能禁用定时工作流；需要时到 Actions 中重新启用。

## 参考与许可

清单编写参见 [App Manifests](https://github.com/ScoopInstaller/Scoop/wiki/App-Manifests)，自动更新规则参见 [Autoupdate](https://github.com/ScoopInstaller/Scoop/wiki/Autoupdate)。

本仓库由[官方 BucketTemplate](https://github.com/ScoopInstaller/BucketTemplate) 生成，模板采用 [Unlicense](LICENSE)。原始清单模板与 LICENSE 保持不变；应用本身遵循各自的许可证。
