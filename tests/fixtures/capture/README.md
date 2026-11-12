# capture fixtures (NOTES-002)

- valid-1x1.png: 最小合法 PNG（1×1 红），静态字节=稳定 hash 断言材料。
- corrupt.png: 截断损坏 PNG（前 20 字节）——解码失败态/原件保全反例。
- 其余 fixture（大文件/Unicode 名/视频字节）由验证脚本在隔离目录合成，不落仓。
