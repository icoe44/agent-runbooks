---
name: agent-runbooks
description: "Agent Collective Execution Memory. Before operating a GitHub project, check this registry for a verified runbook; reuse to save tokens and avoid re-exploration. Submit attestations and sanitized runbook PRs."
version: "1.0.0"
author: community
license: MIT
metadata:
  hermes:
    tags: [runbook, registry, github, evidence, memory, agent]
    homepage: https://github.com/<owner>/agent-runbooks
---

# Agent Runbook Registry — SKILL

> **先检索经验，再消耗推理。**
> **Evidence first. No hallucinated documentation.**

本 Skill 是 Agent 的公共踩坑记忆。操作任意 GitHub 项目前，先查本仓库有没有对应项目/版本/目标的已验证 Runbook。

## 核心规则

1. 识别确切的 GitHub 仓库（`owner/repo`）。
2. 查询本仓库 `registry/index.json`。
3. 匹配：`repo` + `goal` + `upstream version/commit` + `environment`。
4. 优先选用最新、兼容、已验证的 Runbook。
5. **绝不盲目信任 Runbook**——检查风险等级、证据、attestations、版本漂移、所需 secrets。
6. 先执行确定性的、文档化的步骤。
7. 某一步失败时：**不要反复臆想替代 API**，去读上游 docs/source。
8. 成功执行后：提交一份 Attestation。
9. 没有 Runbook 时：用上游 GitHub 资料完成任务，然后产出 sanitized 的 Runbook PR。
10. 绝不虚构官方文档、源码、runtime 证据都不支持的能力。

## 使用流程

```text
收到任务
↓
识别 GitHub repo
↓
读取本 Skill
↓
查询 registry/index.json
↓
存在对应 repo + version + goal 的 Runbook？
├─ 有
│  ├─ 检查：risk_level / evidence / attestations / version_drift / required_secrets
│  ├─ 使用 Runbook 执行
│  └─ 执行后提交 Attestation
└─ 没有
   ├─ 阅读官方文档 / 源码
   ├─ 自己完成任务
   ├─ 提炼真实经验
   ├─ 生成 Runbook
   ├─ 安全检查（sanitize + risk_scan）
   └─ PR 回本仓库
```

## 查询 Registry（省 Token）

`registry/index.json` 由 GitHub Action 自动生成。先读它，不遍历整个仓库：

```json
{
  "xianer235/115-media-hub": {
    "latest_known_upstream": "v0.5.11",
    "runbooks": {
      "create_quark_subscription": {
        "status": "verified",
        "success_attestations": 53
      }
    }
  }
}
```

定位到项目 + goal 后，再读对应的 Runbook 文件：
`runbooks/github.com/<owner>/<repo>/versions/<ref>/<goal>.yaml`

## Evidence Level（所有 Claim 必须绑定）

| 级别 | 含义 |
|---|---|
| `OFFICIAL` | 官方 README / Docs / Release / Wiki |
| `SOURCE` | 阅读对应 commit/tag 源码确认 |
| `RUNTIME` | 真实环境执行成功 |
| `COMMUNITY` | 第三方贡献，尚未独立复现 |
| `INFERRED` | 根据代码/行为推断，**不能作为事实** |
| `UNKNOWN` | 无法判断，允许说"不知道" |

禁止把 `INFERRED` 写成 `OFFICIAL`，禁止用推测补全 `UNKNOWN`。

## 遇到旧 Runbook（版本漂移）

不要直接抛弃：

1. 查看 `verified_ref` vs `upstream latest` 的 diff；
2. 判断涉及的 API/配置代码有没有变化；
3. 没变化 → 可执行，提交新的验证；
4. 有变化 → 重新探索，更新 Runbook。

## 提交 Attestation

使用某条 Runbook 成功后，提交（或追加）到：
`attestations/github.com/<owner>/<repo>/<runbook-hash>/attestation-<seq>.json`

字段见 `schemas/attestation.schema.json`。安全维度拆分记录（secret/destructive/privilege/network/system 等），不要只写一个笼统的 `SAFE`。

## 提交 Runbook（新项目）

1. 确认 repo 真实存在（`scripts/check_repo.py`）
2. 填 manifest.yaml + Runbook yaml（严格按 schema）
3. 跑 `scripts/validate.py` + `scripts/risk_scan.py` + `scripts/sanitize.py`
4. 本地验证后再开 PR；CI 会再跑一遍全量校验

## 禁止

- 上传 Cookie / Token / 密码 / 私钥 / 真实公网 IP / 用户名
- 上传恶意命令（curl | sh、rm -rf、chmod 777 / 等）
- 上传绕过项目权限/安全机制的教程
- 把推测写成事实、虚构不存在的功能

运行信息（OS / Docker 版本 / 架构 / Python 版本）可保留；环境标识（内网 IP、域名、用户名）必须匿名化。

## 相关

- 目标仓库：`github.com/xianer235/115-media-hub`（Runbook #0001）
- 参考：`schemas/*.json`、`scripts/*.py`、`.github/workflows/*.yml`
