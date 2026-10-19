# 维护说明

## 文件用途

| 路径 | 用途 |
| --- | --- |
| `My_Routing.ini` | 当前覆写模块源码，不包含节点订阅或节点凭据 |
| `README.md` | 安装、分组、更新和恢复说明 |
| `docs/troubleshooting.md` | 常见故障的检查顺序与反馈要求 |
| `scripts/validate.py` | 模块结构、规则源和 Mihomo 合成配置检查 |
| `tests/test_validate.py` | 发布约束与分流优先级的回归测试 |
| `.github/workflows/check.yml` | 检查与 `stable` 发布流程 |
| `previous/My_Routing.ini` | 首次创建 `stable` 时使用的历史回滚种子，不是当前上一版 |

日常修改在 `main` 分支完成。路由器订阅 `stable` 分支中的 `My_Routing.ini`。

## 修改配置

- 修改前查阅 [OpenClash 用户指南](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/SKILL.md)、[覆写模块示例](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/17-overwrite-module-examples.md)及对应子文档。
- 保留局域网直连前缀、国内服务例外和最终兜底；特定服务规则先于通用分类。
- 新增规则源时，确认 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 中存在相应 MRS 文件，并使用独立的 `rule_provider/*.mrs` 路径。
- 调整分组或默认线路时，同步修改 README，并为会影响既有路由优先级的变动补充回归测试。
- 分组与规则可以使用公开服务域名；个人订阅、节点列表和设备配置保存在仓库外。

## 本地检查

使用 Python 3.12 或更新版本，在仓库根目录安装依赖并运行测试：

```sh
python -m pip install --requirement requirements.txt
python -m unittest discover -s tests -v
python scripts/validate.py My_Routing.ini --offline
```

离线检查只验证结构。发布前还需下载规则源并使用 Mihomo 检查合成配置：

```sh
python scripts/validate.py My_Routing.ini --core /path/to/mihomo --work-dir .validation
```

将 `/path/to/mihomo` 替换为本机可执行文件的路径；Windows 可使用 `mihomo.exe`。正式发布采用工作流中固定版本和校验和的 Mihomo。规则源会写入指定的工作目录，不需要真实节点订阅。

检查覆盖 YAML、分组引用与循环、局域网优先级、规则源地址及下载内容，并将本机回环地址上的合成节点交给 Mihomo 进行配置测试。检查不代表真实节点可用、特定服务解锁或所有 OpenClash 版本均兼容。

## 发布与恢复

推送 `main`、定时任务或手动运行工作流时，检查成功后才执行发布；Pull Request 仅检查。工作流会确认通过检查的提交仍是最新 `main`，较旧的检查结果不会替换 `stable`。

`stable` 分支仅包含：

- `My_Routing.ini`：当前通过检查的模块。
- `My_Routing.previous.ini`：上一份已发布模块。
- `SHA256SUMS`：两份模块的校验和。

模块内容改变时，原 `stable/My_Routing.ini` 会成为 `My_Routing.previous.ini`。仅更新文档、重复运行检查或发布相同模块时，不会推进回滚副本。

`previous/My_Routing.ini` 仅用于首次创建发布分支。该文件保留历史版本，不应为满足当前检查约束而改写；正常回滚应使用 `stable` 分支中的 `My_Routing.previous.ini`。历史配置仍需确认与实际插件、内核和节点订阅兼容。

路由器上的恢复操作见 [README 的更新与恢复](README.md#更新与恢复)。

## 公开内容检查

提交前检查 `git status`、待提交差异和新增文件。仓库不接收以下内容：

- 完整订阅链接、查询参数中的令牌、节点密码、UUID、私钥或控制面板密钥。
- 真实节点配置、路由器备份、完整调试日志和抓包文件。
- 账号邮箱、设备信息、私人路径或含上述内容的截图。

`.gitignore` 只能帮助排除常见本地文件，不能替代人工审阅。反馈问题时保留错误码、相关规则和必要上下文，敏感值用占位符替换；不可逆的遮盖应覆盖图片中的实际内容。

如果凭据已经提交到公开仓库，应先在服务端撤销或更换凭据，再评估历史清理。只删除当前文件不能移除 Git 历史中的副本。
