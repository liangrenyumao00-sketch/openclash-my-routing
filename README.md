# 我的 OpenClash 分组和分流

原订阅继续提供节点；`My_Routing.ini` 接管分组和分流。此文件没有节点密码、订阅地址或令牌，可以公开托管。它是 OpenClash 覆写模块，不能当作普通 YAML 订阅导入。

## 它怎么分流

- 局域网及标准本地域名直连。
- AI 官方服务、YouTube、Netflix、Disney+、Spotify、谷歌、社交通讯、开发平台、Steam 游戏、微软、苹果和 PayPal 可分别选线路。
- 苹果、微软、Steam 的已收录国内服务优先直连。
- 国内域名名单走直连；国外域名名单走代理。
- 尚未识别的域名也先走代理，减少陌生国外网站被 IP 归属误判为国内的情况。代价是少数尚未收录的国内网站也会先走代理。
- 只有没有可识别域名的连接，才继续按中国 IP 名单判断。名单不保证百分之百准确。

规则来自 MetaCubeX/meta-rules-dat 的分类库，每 24 小时更新。分类包含许多网站，配置里的几十行代表整套名单，并非只覆盖几十个网站。没有按用户提供的网站逐个写规则，也没有用 `.cn`、`.com` 后缀或 `ai` 关键字猜用途。

任意第三方 AI 中转站无法自动识别为 AI 服务：它们按国内/国外名单分流，未收录的默认代理。`/v1` 是网址路径，不是域名；同一个域名的主页和 API 使用相同分流。代理线路也不能保证一个网站可访问，网站自身故障、DNS、线路和账号地区限制仍可能影响结果。

## 第一次怎么装

以下按你当前的 **v0.48.002** 界面操作：

1. 打开 **服务 → OpenClash → 运行状态**，点击顶部 **覆写模块** 按钮。
2. 弹出窗口后，点 **+ 添加新模块 → 订阅链接**。
3. 名称填 `My_Routing`；“配置”选择 **添加到所有配置文件**；“类型”选择 **http**。选择类型后才会出现“订阅地址”输入框。
4. 在“订阅地址”中填入你的 `My_Routing.ini` 原始文件地址；更新时间选 **周日 4:00**，然后点击 **添加**。
5. 打开 `My_Routing` 的模块开关，再到运行状态页点击 **重启**。初次添加默认关闭，必须手动打开。
6. 代理模式使用 **策略代理 / Rule**。在控制面板选择节点：默认“节点选择”使用自动选择，“国内网站”使用 DIRECT。

这是运行状态页的“覆写模块”按钮，与菜单中的“覆写设置”不是同一个入口。当前 dev 版可使用两步向导；v0.48.002 按上述表单直接添加，无需寻找“下一步”。如果安装版本没有此按钮，应先确认版本。

模块会替换原分组和原规则，添加自己的规则库，但保留原订阅节点和代理提供商。订阅更新后，OpenClash 重启时会重新应用它。规则源每 24 小时更新；分组文件每周日 4 点拉取，下载成功后自动重启应用，可能有短暂连接中断。手动修改在线文件后，也可刷新模块并重启。

地区分组按节点名称归类。机场没有对应地区，或节点名无法识别时，该组显示拒绝连接，应选择其他实际存在的地区或“节点选择”；不会悄悄换到别的国家。AI 和流媒体需要选服务支持的节点，不能用测速结果保证解锁。你自定义的局域网域名（例如公网形式的 NAS 域名）如果不在本地名单中，需要另加直连例外。

模块启用后会关闭 IPv4/IPv6 的“地区绕行”，避免部分连接提前跳过规则；国内网站仍由名单判断为直连。若有其他模块同时修改分组/规则，也应检查覆写顺序，避免互相覆盖。

## 在线地址怎么得到

在你自己的 GitHub 公开仓库放 `My_Routing.ini`。打开文件，点 **Raw** 获取原始文件地址，把这个地址填到上面的“订阅链接”。只上传此模块和说明，绝不要上传原订阅、节点文件或调试日志。

之后编辑 GitHub 上的文件并提交，路由器会按设定时间拉取。它仍使用原机场的节点，机场换节点时不用重写分组。已有原订阅地址不必改成这个地址。

## 怎么核验和退回

启用后，控制面板应出现本模块的 22 个分组。检查“连接”页面，确认国内站命中“国内网站”，国外站命中“国外网站”或相应服务组。本地使用 Mihomo v1.19.32 加测试节点检查，配置语法和组名引用通过，22 份规则文件下载成功；本地验证不能保证所有网站可用，仍需在路由器的连接页面确认实际分流。

特殊订阅若用旧分组作为节点的链式代理出口（dialer-proxy）或代理提供商的下载出口（proxy），替换分组前还需检查这些引用。普通内嵌节点没有这一问题。

要恢复原配置：关闭 `My_Routing` 的开关，再重启 OpenClash。出现启动/访问异常时，按官方指南先生成调试日志：**运行日志 → 调试日志 → 生成日志**。

## 依据

- [OpenClash 用户指南入口](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/SKILL.md)
- [12-subscribe-config.md §12.1–12.3](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/12-subscribe-config.md)：节点订阅更新。
- [16-overwrite-module-format.md §16.1.1、§16.2.3](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/16-overwrite-module-format.md)：入口、替换数组、重启生效。
- [17-overwrite-module-examples.md §17.5.1](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/17-overwrite-module-examples.md)：在线更新与重启。
- [07-page-overview.md §7.3–7.4](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/07-page-overview.md)：规则模式、地区绕行。
- [08-settings-mode-traffic.md §8.3.5](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/08-settings-mode-traffic.md)：地区绕行会使部分连接提前跳过规则。
- [Mihomo 策略组](https://wiki.metacubex.one/config/proxy-groups/)、[路由规则](https://wiki.metacubex.one/config/rules/)、[规则提供商](https://wiki.metacubex.one/config/rule-providers/)。
- [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)：规则分类与在线数据。
