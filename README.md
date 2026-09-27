# Lunophira Wiki Mirror

这是 **琉诺菲拉（Lunophira）** Miraheze Wiki 的只读镜像仓库。

- 原站：https://lunophira.miraheze.org/wiki/
- 原站是唯一正式版本；本仓库不作为编辑源。
- 本仓库用于全文搜索、备份和 AI 读取。

## 当前同步状态

Miraheze 当前会对 GitHub-hosted runners 和部分数据中心网络返回 Cloudflare 403/“Just a moment...”挑战，因此自动云端直抓目前不可用。

仓库保留了两条同步路径：

1. `sync_wiki.py` + `.github/workflows/sync.yml`
   - 直接调用 Miraheze MediaWiki API。
   - 当前会被 403 拦截，所以只保留为手动备用方案，未来 Miraheze 放开后可直接恢复。

2. `import_dump.py` + `.github/workflows/import-dump.yml`
   - 当前可靠方案。
   - 从 Miraheze 的 **Special:DataDump** 生成 MediaWiki XML dump。
   - 将 `.xml` / `.xml.gz` / `.xml.bz2` 文件放进仓库的 `imports/` 目录。
   - GitHub Actions 会自动解析并生成镜像。

MediaWiki 的 DataDump 扩展就是用于生成、下载 wiki dump 的；Miraheze 默认部署了这一扩展。

## 镜像输出

- `wiki/main/`：正文词条原始 MediaWiki 源码
- `wiki/template/`：模板
- `wiki/category/`：分类页
- `wiki/module/`：Lua 模块
- `index.json`：机器可读页面索引
- `all-pages.md`：所有正文词条合并文件，适合全文搜索和 AI 阅读

## 导入一次 XML dump

在 Miraheze 登录站长账号后，打开：

`Special:DataDump`

生成 XML dump（通常是 `.xml.gz`），下载后把文件上传到本仓库的 `imports/` 目录。

上传完成后，`Import Lunophira XML dump` 工作流会自动运行并生成镜像。

也可以手动运行：

```bash
python import_dump.py path/to/dump.xml.gz
```

## 说明

XML dump 包含 wiki 页面内容与修订信息，但通常不包含上传图片本体、用户账号或日志等站点级数据。对“让 AI 能读取世界观正文”这个目标来说，正文 XML 已经足够。


## 当前镜像快照（2026-09-27）

已从 Miraheze XML dump 导入：

- 52 个导出页面的索引：`index.json`
- 29 个主名字空间正文词条的完整语料：`corpus/all-pages-01.md` ～ `all-pages-06.md`
- 已验证 GitHub 连接可以直接读取该语料（例如“灵魂”“玛纳泽永久契约联邦”等词条）。

GitHub Code Search 对新提交存在索引延迟；即使搜索暂时无结果，也可以通过仓库文件接口直接读取 corpus。
