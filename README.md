# OpenClash 分流配置

用于 OpenClash 的分组和分流规则。节点继续使用原来的订阅，启用后由 `My_Routing.ini` 管理分组和分流。

国内网站默认直连，国外网站走代理。ChatGPT、Claude、Gemini 分开选线路，各地区支持自动更换备用节点，也可以手动固定节点。

[![配置检查](https://github.com/liangrenyumao00-sketch/openclash-my-routing/actions/workflows/check.yml/badge.svg)](https://github.com/liangrenyumao00-sketch/openclash-my-routing/actions/workflows/check.yml)

## 安装

先在 OpenClash 中添加可用的节点订阅。下面以 **v0.48.002** 为例。

1. 打开 **服务 → OpenClash → 运行状态**，点击顶部的 **覆写模块**。
2. 点击 **添加新模块 → 订阅链接**，按下表填写。

   | 项目 | 填写内容 |
   | --- | --- |
   | 模块名称 | `My_Routing` |
   | 配置文件 | 添加到所有配置文件 |
   | 类型 | `http` |
   | 订阅地址 | 下方的完整地址 |
   | 更新时间 | 每周日 4:00，也可自行调整 |

   ```text
   https://raw.githubusercontent.com/liangrenyumao00-sketch/openclash-my-routing/stable/My_Routing.ini
   ```

3. 点击 **添加**，打开 `My_Routing` 的开关，再回到运行状态页点击 **重启**。
4. 代理模式选择 **规则（Rule）**。打开控制面板，在“节点选择”中选择线路，或保留默认的“自动选择”。

这是覆写模块，请从运行状态页的 **覆写模块** 按钮添加，不要填到节点订阅栏。其他版本的界面可能略有不同。

## 分组

共 36 个分组。平时主要使用服务分组和地区分组，自动备用组按需展开即可。

| 分组 | 用途 |
| --- | --- |
| 节点选择、自动选择 | 手动选节点，或按检测延迟自动选择 |
| 香港、台湾、日本、新加坡、美国、韩国节点 | 每个地区都可选自动备用或具体节点 |
| 香港自动等 6 个自动组 | 使用该地区顺序靠前的可用节点，失效后换备用 |
| ChatGPT、Claude、Gemini | 三项 AI 服务分别选择线路，默认美国节点 |
| AI服务、谷歌服务 | 其他已收录的海外 AI 服务及 Google 服务 |
| YouTube、Netflix、Disney+、Spotify | 视频和音乐服务 |
| Telegram、TikTok、社交通讯 | Telegram 和 TikTok 单独设置，其余社交服务合并管理 |
| 开发平台、游戏平台 | GitHub、开发工具，以及 Steam 等海外游戏平台 |
| 网盘下载 | OneDrive、Dropbox、MEGA |
| 学术网站、动漫平台 | 海外学术站点、巴哈姆特及国际版哔哩哔哩 |
| 微软服务、苹果服务、金融支付 | Microsoft、Apple、PayPal 等 |
| 国内网站、国外网站 | 国内外网站的默认线路 |

大部分服务默认跟随“节点选择”；AI 和 TikTok 默认美国节点，动漫平台默认台湾节点。“国内网站”默认 `DIRECT`（直连）。

地区内的自动备用每 5 分钟检测一次，闲置时减少检测。节点失效后通常要等检测才能更换；不会仅因另一条线路延迟更低就切换，优先节点恢复后可能切回。要保持固定出口，在服务或地区分组中选择具体节点。

从旧版升级后，原来的手动选择可能会保留。需要自动备用时，在“香港节点”等分组中选“香港自动”等对应选项。

## 分流方式

- 局域网地址和常见本地域名直连。
- 已收录的服务进入对应分组；苹果、微软、游戏和开发工具的国内服务优先直连。
- 国内域名名单走直连，国外域名名单走代理。
- 未收录的域名默认走代理，因此少数国内网站也可能走代理。
- 没有识别到域名的连接，按中国 IP 名单判断，其余走代理。

规则名单来自 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)，每 24 小时检查一次更新。

## 更新与恢复

模块按安装时设置的时间更新，下载成功后会自动重启 OpenClash，连接可能短暂中断。需要立即更新时，在覆写模块列表中刷新 `My_Routing`，完成后重启。

正常订阅使用上面的 `stable` 地址。新配置会先检查格式、分组引用、规则下载地址，并交给 Mihomo 检查；全部通过后才发布到 `stable`，检查失败时保留原版本。规则名单仍由各规则源每日更新。

已使用旧 `main` 地址的用户，可在模块设置中把地址里的 `/main/` 换成 `/stable/`，保存后刷新。

自行维护时，可 Fork 本仓库，在主分支修改 `My_Routing.ini`；启用 GitHub Actions 后，通过检查的版本会自动发布到自己的 `stable` 分支。

恢复原分组和规则：关闭 `My_Routing` 的开关，然后重启 OpenClash。

仓库保留[上一版配置](https://raw.githubusercontent.com/liangrenyumao00-sketch/openclash-my-routing/stable/My_Routing.previous.ini)。需要退回时，可下载保存，作为本地覆写模块使用，同时关闭在线模块以免重复覆盖。

## 使用说明

- 分流按域名匹配。第三方 AI 中转站不一定归入“AI服务”，未收录的会进入“国外网站”。
- 地区分组按节点名称筛选。某个地区没有可用节点时，选择其他地区或“节点选择”。
- “自动选择”按延迟挑选节点，地区自动组负责备用切换。检测通过不代表 AI 或流媒体一定可用；有地区限制的服务需要另行确认节点支持情况。
- 在控制面板的 **连接** 页面，可以查看网站命中了哪条规则、使用哪个分组和节点。
- 电脑或手机应通过 OpenClash 所在路由器上网。多层路由时，设备网关可以是下一级路由器，关键是后续流量和 DNS 仍经过 OpenClash。IPv6 若从其他网关出站，会绕开这套 IPv4 分流；应单独核对。
- 模块会关闭 IPv4/IPv6 的“区域绕过”，让流量交给这里的规则判断。关闭模块后，如需恢复原来的区域绕过设置，应在运行状态页手动调整。
- 启动或访问异常时，可在 **运行日志 → 调试日志 → 生成日志** 中收集排查信息。

<details>
<summary>与其他配置一起使用</summary>

模块会替换原配置的分组和规则，保留原订阅节点，并添加所需规则库；同名规则库会被覆盖。其他覆写模块若也修改分组或规则，可能互相覆盖。

使用链式代理、自定义 DNS 或特殊代理提供商时，应检查是否还引用了原来的分组名称。自定义 NAS 等本地域名若不在直连名单中，需要添加直连规则。

</details>

相关文档：[OpenClash 覆写模块](https://raw.githubusercontent.com/vernesong/OpenClash/dev/.github/skills/openclash-user-guide/17-overwrite-module-examples.md)（§17.1、§17.5.1）。
