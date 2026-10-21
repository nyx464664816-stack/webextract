# WebExtract 状态页：上传与发布说明

## 要上传的文件（路径与仓库根目录一致）
- `.github/workflows/status.yml`：每 5 分钟跑一次探测（GitHub 高峰期可能延迟），也可以在 Actions 页面手动运行
- `status/probe.py`：只读探测脚本，只用 Python 标准库，不需要任何密钥
- `status/README.md`：本说明

## 探测什么（全部只读：不付款、不带 X-Billing、不消耗免费额度、不碰 /buy/*）
网站首页、`/health`（含 `"ok":true`）、`/v1/extract` 和 `/v1/markdown`（不带付款头时必须返回规范的 402，7 条主网全在、没有测试网）、`POST /mcp`、`/openapi.json`、`/.well-known/x402`、两个域名的 TLS 证书（剩余不足 14 天就标红）。
输出 `index.html`、`status.json`（当前状态）和 `history.json`（大约 7 天的历史，用来算可用率）。

## 发布步骤
1. 把上面 3 个文件提交到默认分支 `main`。
2. 打开 Actions → `status-page` → Run workflow，手动跑一次。成功后仓库里会多出 `gh-pages` 分支，里面带 `CNAME`（内容是 status.webextract.dev）。
3. Settings → Pages：Source 选 **Deploy from a branch**，Branch 选 **gh-pages**，目录选 **/ (root)**，Custom domain 填 `status.webextract.dev`。
4. Cloudflare DNS 加记录：类型 `CNAME`，名称 `status`，目标 `nyx464664816-stack.github.io`，代理状态先设成 **DNS only（灰云）**，等 GitHub 签发好证书。
5. 证书签好后，在 Pages 设置里勾选 **Enforce HTTPS**。

## 注意
- workflow 只用仓库自带的 `GITHUB_TOKEN`（权限 contents: write），只往 `gh-pages` 推送，不需要另外配置密钥。
- 每次运行都会覆盖推送 `gh-pages`，这个分支只保留一个提交，不会越积越大。
- 公开仓库的定时任务：如果仓库 60 天没有活动，GitHub 会自动停用定时任务（以 GitHub 官方文档为准），到时候在 Actions 页面重新启用即可。
- `/health` 带 `x402_networks` 数组时（价格补丁上线后），会额外检查 7 条主网都在、没有这个字段时只看 `"ok":true`。
