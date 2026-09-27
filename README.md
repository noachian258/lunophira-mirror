# Lunophira Wiki Mirror

这是 **琉诺菲拉（Lunophira）** Miraheze Wiki 的自动只读镜像。

- 原站：https://lunophira.miraheze.org/wiki/
- 原站是唯一正式版本；本仓库不作为编辑源。
- GitHub Actions 每天自动从 Miraheze 拉取公开页面。
- 也可以在 Actions 页面手动运行同步。

## 目录

- `wiki/main/`：正文词条原始 MediaWiki 源码
- `wiki/template/`：模板
- `wiki/category/`：分类页
- `wiki/module/`：Lua 模块
- `index.json`：全部已同步页面的机器可读索引
- `all-pages.md`：所有正文词条的合并版本，便于全文搜索和 AI 阅读
- `sync_wiki.py`：同步脚本

## 同步方式

同步脚本通过 Miraheze 的公开 MediaWiki API 读取页面，不需要账号或密钥，也不会写入原 Wiki。

如果同步没有检测到变化，GitHub Actions 不会产生新提交。
