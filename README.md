# Skill Helper

Skill Helper 是一个面向多用户的技能平台示例项目，目标是把「技能创建 / 修改 / 使用」做成可部署的 Web 服务。

当前仓库内置了 `copaw-skill-platform`，提供 Docker 化运行、基础权限模型、技能版本管理和异步运行任务能力。

## 项目结构

```text
.
├─ .github/workflows/
│  └─ copaw-skill-platform-docker-multiarch.yml
└─ copaw-skill-platform/
   ├─ docker-compose.yml
   ├─ api/
   │  ├─ Dockerfile
   │  └─ app/
   └─ README.md
```

## 核心能力（MVP）

- 多用户注册与登录（JWT）
- 技能创建、修改、版本化保存
- 可见性控制（`private` / `shared` / `public`）
- 协作者角色（`editor` / `viewer`）
- 异步运行任务（worker 消费队列）
- Web 管理页（技能管理与运行）

## 本地启动

```bash
cd copaw-skill-platform
docker compose up --build
```

服务地址：`http://localhost:8080`

## 多架构镜像构建（GitHub Actions）

工作流文件：`.github/workflows/copaw-skill-platform-docker-multiarch.yml`

- 构建平台：`linux/amd64`、`linux/arm64`
- `pull_request`：仅构建校验
- `push main/master`、`push tag(v*)`、`workflow_dispatch`：构建并推送到 GHCR

镜像名：

```text
ghcr.io/<owner>/<repo>/copaw-skill-platform
```

## 生产化建议

1. 用真实沙箱替换当前模拟 Runner（容器隔离 + 资源限制）
2. 增加审批流、审计日志与回滚
3. 增加组织/团队维度权限模型
4. 接入对象存储和备份策略

## 说明

这是一个可运行的工程骨架，适合从 0 到 1 快速验证产品方向，再逐步增强安全与治理能力。
