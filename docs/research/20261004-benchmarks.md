# Auto Notes：业界调研与取舍

调研日期：2026-10-04。以下使用官方产品帮助/文档；是交互和能力的对照，不是价格、性能或全平台一致性的评测。官方页面可能随产品更新；硬件和语言支持须实施时再次核实。

| 参考 | 本轮核实的能力与来源 | Auto Notes 的取舍 |
|---|---|---|
| OneNote | [Quick Notes](https://support.microsoft.com/en-us/onenote/onenote-help-and-learning/create-quick-notes) 描述小窗记录及保存到笔记本；[输入与格式](https://support.microsoft.com/en-us/onenote/take-and-format-notes) 覆盖文字、图像、手写、音视频、列表、链接及自动保存 | 借鉴快速入口到完整记录的连续性；先完成可靠保存，不复制无限画布 |
| Apple Notes | [Mac Quick Note](https://support.apple.com/guide/notes/create-a-quick-note-apdf028f7034/mac) 提供快捷入口、网页选区及来源链接 | 卡片默认 Inbox，保存来源与可回访定位；快捷键由宿主适配 |
| Google Keep | [提醒](https://support.google.com/keep/answer/3187168?hl=en-GB) 与 Tasks/Calendar 联动；[绘图](https://support.google.com/keep/answer/6395656?hl=en) 提供便签绘图入口 | 清单、色标、置顶、归档进入常见需求；提醒交系统调度，不建立第二套任务系统 |
| 锤子便签 | [官方 Markdown 示例](https://cloud.smartisan.com/apps/note/md.html) 展示轻量排版及图片分享；该页面较旧，不据此推断今天的移动端/同步能力 | 简洁书写、可读卡片、后续长图分享；不照搬非标准 Markdown 的私有语法 |
| HUAWEI Notes | [官方介绍](https://consumer.huawei.com/en/mobileservices/notes/) 展示笔刷、手写增强及录音笔记回放；部分能力限定平板和版本 | 作为手写深度产品参考；不把平板笔记能力直接列成所有手机的首版承诺 |
| Goodnotes | [手写识别语言](https://support.goodnotes.com/hc/en-us/articles/7353727932047-Handwriting-Recognition-and-Search-Languages-in-Goodnotes)、[搜索](https://support.goodnotes.com/hc/en-us/articles/7353743594127-How-to-Search-Your-Notes) 区分手写与已有 OCR 层的 PDF | 保存原始笔迹/图像，识别是独立文本层；中文、英文分别测，不借用产品宣传推断跨端成熟度 |
| Notability | [手写和工具设置](https://support.gingerlabs.com/hc/en-us/articles/5955260981786-Settings-Appearances-Tools-Gestures) 描述识别语言、形状及掌托等设置 | 用户未具名的付费笔记应用，用 Notability 作补充对照；不是 Apple 自家付费 Notes 的确认 |
| Apple 手写 | [iPad Notes 手写](https://support.apple.com/en-sa/guide/ipad/ipada87a6078/ipados) 描述设备/语言条件及整理手写文字 | 自动美化和可编辑手写属于较深产品能力，安排 v0.7+ |
| Raycast | [剪贴板历史](https://manual.raycast.com/clipboard-history) 含搜索、固定、删除、保留时长和内容动作 | copy-paste bin 提供历史与选择，Notes 接收用户选定条目；不各自常驻采集一套历史 |

## 结论

快速记录必须先解决“稍后能找回来”：几步完成记录、真实持久化、离线和错误恢复比 AI 自动整理更先。媒体先收好原资产，再异步提取预览/OCR/摘要。便签是个人知识入口，Jade 是知识工作台，两者共享对象而各自提供界面。

手写需求应纳入，但分层：v0.6 必须能附加手写图像并保留原件；笔迹资产模型预留；有真实设备和 AutoUI 输入支持时做限定设备的画笔/识别原型。完整 Goodnotes 式页面、压感、掌托、公式、录音同步和笔迹风格重写留到 v0.7 或更远。手机小屏主要仍是输入、拍照、分享接收；平板/触控笔才是深手写的主要场景。

这些取舍是 Auto Notes 的设计判断，不是被调研产品已经提供的 Auto 生态联动。
