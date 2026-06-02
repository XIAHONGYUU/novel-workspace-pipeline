---
title: 如何在wsl中安装codex并使用
aliases:
  - WSL 安装 Codex
tags:
  - codex
  - wsl
  - guide
created: 2026-03-29
---

# 如何在wsl中安装codex并使用

## 文档信息
- 状态：`可用`
- 场景：`在 WSL 环境中安装并使用 Codex`
- 适用系统：`Windows + WSL2`

## 一句话说明
这篇笔记用于记录如何在 Windows 的 WSL 环境中安装 Codex、完成基础配置，并开始在终端中使用。

## 前置条件
- [ ] Windows 已启用 `WSL2`
- [ ] 已安装一个 Linux 发行版，例如 `Ubuntu`
- [ ] 可以正常打开 WSL 终端
- [ ] 已安装 `git`
- [ ] 已安装 `Node.js` 或其他 Codex 依赖运行环境
- [ ] 已准备可用的 API Key 或账号凭证

## 安装步骤

### 1. 更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 安装基础工具
```bash
sudo apt install -y curl git build-essential
```

### 3. 安装运行环境
如果 Codex 依赖 Node.js，可先安装：

```bash
sudo apt install -y nodejs npm
node -v
npm -v
```

如果项目要求更高版本，优先使用 `nvm` 管理 Node.js。

## 安装 Codex
> 这里的安装方式取决于你实际使用的 Codex 分发形式，例如 npm 包、源码仓库或内部安装脚本。

常见方式示例：

### 方式一：通过 npm 全局安装
```bash
npm install -g codex
```

### 方式二：从源码仓库安装
```bash
git clone <your-codex-repo-url>
cd <your-codex-repo-name>
npm install
```

## 配置环境

### 配置 API Key
将密钥写入 shell 配置文件，例如 `~/.bashrc`：

```bash
export OPENAI_API_KEY="your_api_key_here"
```

然后执行：

```bash
source ~/.bashrc
```

### 验证环境变量
```bash
echo $OPENAI_API_KEY
```

## 开始使用

### 启动 Codex
```bash
codex
```

或者在源码目录中运行：

```bash
npm run start
```

### 常见使用方式
- 在项目目录启动 Codex
- 让 Codex 帮你阅读代码
- 让 Codex 修改文件
- 让 Codex 生成 Obsidian 笔记或开发文档

## 推荐目录习惯
```text
~/projects/
  my-app/
  notes/
  sandbox/
```

建议把代码项目与笔记仓库分开，便于管理。

## 常见问题

### 1. 命令不存在
检查：
- 是否已经正确安装
- 是否加入 `PATH`
- 是否重启过终端

### 2. API Key 无效
检查：
- 环境变量是否生效
- Key 是否复制完整
- 账号权限是否正常

### 3. WSL 中文路径或权限问题
建议优先在 Linux Home 目录中工作，例如：

```bash
cd ~/projects
```

不要长期直接在 `/mnt/c/` 下做高频开发操作。

## 相关笔记
- [[WSL 基础配置]]
- [[Node.js 安装与版本管理]]
- [[Obsidian 笔记规范]]
- [[Codex 常用命令]]

## 可复用模板
```md
---
title: <标题>
tags:
  - codex
  - wsl
created: 2026-03-29
---

# <标题>

## 目标

## 前置条件

## 安装步骤

## 配置方法

## 使用示例

## 常见问题

## 相关笔记
```
