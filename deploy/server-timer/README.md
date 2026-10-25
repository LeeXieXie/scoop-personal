# Server scheduler deployment

服务器版独立计时器，默认每 3 分钟（180 秒）触发本仓库的全包 Upstream Watch，
可用 `--interval 300` 改为 5 分钟。宝塔用户优先看 [宝塔中文部署步骤](BAOTA.md)
和可直接粘贴的 [compose.baota.yml](compose.baota.yml)。
只用 Python 标准库，不需要安装 gh，不需要开放服务器端口。
**以下为部署方法，不表示已经安装到你的服务器。**
优先选 Docker Compose 或 systemd 其中一种，先在服务器配置仅限本仓库的
Actions 读写 Token，验证两次自然运行成功后再停用原 Windows 定时器。
不要将真实 Token、SSH 密码或私钥发送到聊天中。

The server only wakes the existing GitHub `upstream-watch.yml` workflow. The
workflow checks all bucket packages, verifies release readiness and dispatches
Excavator if needed. There is no second list of package/version rules to maintain.

No incoming network ports, database, web UI or GitHub CLI installation is needed.
Python 3.11+ and outbound HTTPS to api.github.com are sufficient.

## Credentials

Create a fine-grained GitHub token scoped ONLY to `LeeXieXie/scoop-personal`, with
repository **Actions: read and write** (and automatically granted Metadata read).
Set an expiry and renew it before expiry. Keep it on the server, not in Git, chat,
shell history, image build arguments or a Docker image. A GitHub App installation
token with equivalent permissions can also work, but its renewal must be managed
separately. The program does not renew tokens.

The program reads `GH_TOKEN_FILE` or `GH_TOKEN`, not both. Prefer a mounted file.
Create `github-token` next to this README using your server's editor, put only the
token in it, and restrict its permissions. Do not paste an actual token into the
example commands. `.gitignore` and `.dockerignore` exclude local token files.

Only one scheduler deployment should be enabled. Queue checks are best effort,
not a distributed lock across independent Windows, Docker and systemd schedulers.
Existing workflow concurrency still serializes updates.

## Prebuilt image release and upgrades

The transport fix is released as
`ghcr.io/leexiexie/scoop-upstream-timer:1.0.2` after the repository's **Publish
Server Image** workflow succeeds. It publishes Linux amd64 and arm64 images,
updates the rolling `latest` tag, and retains a full `sha-<source commit>` tag.
Earlier `1.0.0` and `1.0.1` release tags are not replaced by this release. The
workflow checks both platform manifests and source-revision/version labels,
then runs the offline regression suite against each published platform image.
Its live `--check` is read-only; publication does not install or upgrade BaoTa.

For the environment-only BaoTa deployment, follow [BAOTA.md](BAOTA.md), keep the
existing server-side `GH_TOKEN`, and set the image to `:1.0.2` to pin this release
or keep `:latest` for rolling upgrades. From this directory, after publication:

```sh
docker compose -f compose.baota.yml pull scheduler
docker compose -f compose.baota.yml up -d --force-recreate scheduler
```

These steps apply to upgrades from either `1.0.0` or `1.0.1`. Keep
`command: ["--interval", "180"]` for the default three-minute cadence; an old
explicit `300` overrides the image default. Restarting the old container alone
does not update its image, environment or command. Only keep one scheduler.
The local-build Compose option that follows uses a different Compose file.

## Option A: Docker Compose

Run on the server from this directory (`deploy/server-timer`):

```sh
# Edit github-token securely before starting. The non-root container uses UID 10001.
sudo chown 10001:10001 github-token
sudo chmod 600 github-token
docker compose build
docker compose run --rm scheduler --check
docker compose up -d
docker compose logs --tail=50 -f scheduler
```

The container starts a check immediately, then follows a 180-second monotonic
start cadence. Request duration is subtracted from the next wait. Missed ticks
are skipped instead of issuing catch-up bursts. Change the Compose command to
`["--interval", "300"]` for a five-minute cadence. It
runs as a non-root user, with a read-only root filesystem, no published ports, and
only a read-only token mount. Log rotation is configured. Keep the token file
readable only to the intended service UID. Compose file-backed secrets are bind
mounts, not an encrypted secret store.

To stop without deleting credentials:

```sh
docker compose down
```

For upgrades, update the checkout, rebuild, then `docker compose up -d` again.
Use `docker compose run --rm scheduler --once` only for an intentional immediate
check, not to claim a natural periodic run succeeded.

## Option B: Linux systemd timer

This option uses a short-lived process every 3 minutes instead of a permanent
Python loop. It requires systemd with `LoadCredential=` support (version 247+),
Python 3.11+ and administrator access for installation. Do not combine with the
Docker option.

From the repository root on the server:

```sh
sudo useradd --system --no-create-home --shell /usr/sbin/nologin scoop-timer
sudo install -d -m 755 /opt/scoop-upstream-timer
sudo install -m 644 scripts/server_upstream_timer.py /opt/scoop-upstream-timer/
sudo install -d -m 700 /etc/scoop-upstream-timer
# Create /etc/scoop-upstream-timer/github-token with a server-side editor.
# It must contain only the token. Never commit it.
sudo chmod 600 /etc/scoop-upstream-timer/github-token
sudo install -m 644 deploy/server-timer/scoop-upstream.service /etc/systemd/system/
sudo install -m 644 deploy/server-timer/scoop-upstream.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start scoop-upstream.service
sudo systemctl status scoop-upstream.service
sudo journalctl -u scoop-upstream.service -n 30 --no-pager
sudo systemctl enable --now scoop-upstream.timer
systemctl list-timers scoop-upstream.timer
```

`useradd` is a one-time step, skip it if the dedicated service user already exists.
The systemd manager reads the root-only credential and exposes a private copy to
the unprivileged service. Never make the token world-readable to fix a permissions
error. The timer uses UTC wall-clock minutes 2, 5, 8, ... 59, with persistent catch-up
after downtime. For alternate five-minute spacing, change `OnCalendar` to
`*-*-* *:02/5:00 UTC`, then reload and restart the timer. `AccuracySec=1s` is a
scheduling preference, not a completion SLA.
The service itself has no network listener and can only write temporary files.

To inspect without dispatching an update trigger:

```sh
sudo systemctl stop scoop-upstream.timer
# A successful oneshot service may display inactive (dead) after it finishes.
sudo systemctl show scoop-upstream.service -p Result -p ExecMainStatus
```

To remove scheduling while keeping files and credentials:

```sh
sudo systemctl disable --now scoop-upstream.timer
```

On systems without systemd, use the Docker option or run the Python process under
an existing process supervisor. Do not assume these unit files work on Windows.

## Direct Python operation

```sh
export GH_TOKEN_FILE=/secure/path/github-token
python3 scripts/server_upstream_timer.py --check
python3 scripts/server_upstream_timer.py --once
python3 scripts/server_upstream_timer.py --interval 180
# Optional five-minute cadence:
python3 scripts/server_upstream_timer.py --interval 300
```

`--check` only queries the GitHub workflow queue. It does not dispatch a workflow
and does not prove that the token has write permission. `--once` attempts one
queue check and dispatch, then exits. The default mode keeps running. Structured
JSON logs distinguish a skipped queued run, accepted dispatch, and API failures.
A successful dispatch only means GitHub accepted the request, not that all
packages were updated or that subsequent CI passed.

Version 1.0.2 negotiates gzip for GET requests and accepts identity responses too.
Both the received wire data and decoded JSON are independently limited to 4 MiB.
Incomplete Content-Length responses and corrupt/truncated gzip are detected
before JSON parsing; retryable transport/JSON failures use bounded GET retries.
Diagnostics contain only safe numeric/allowlisted metadata, never credentials,
response bodies or arbitrary remote header/error text. Persistent failures still
fail closed without dispatching. Queue checks still inspect the latest 100 runs.

GET requests have bounded retry and timeout. A dispatch POST with an uncertain
network/server response is NOT immediately retried, because it might already have
created a run. The next normal cycle checks the queue again. This is best effort
deduplication, not an exactly-once guarantee.

## Acceptance and migration from Windows

1. Verify a real server-triggered GitHub Watch run contains every current bucket
   package and zero detection errors. A no-change run is a valid successful check.
2. If an update is discovered, verify Excavator, the manifest commits and CI.
3. Observe TWO natural server timer cycles and their timestamps. Do not substitute
   two manual invocations for timer evidence.
4. Only after the server deployment passes, disable the old Windows task:
   `Disable-ScheduledTask -TaskName ScoopPersonalUpstreamWatch` on the Windows PC.
5. Keep GitHub cron as fallback. Monitor the last successful Watch run age and
   token expiry. A stopped server or expired token cannot trigger new checks.

This repository provides deployment files. Until actual server commands and logs
have been checked, it does NOT mean the program has been installed on your server.
