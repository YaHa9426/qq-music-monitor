markdown
# QQ 音乐免费会员活动监控

自动监控 QQ 音乐官方免费领会员活动，发现新活动时通过 Server酱 推送到微信。

## 工作原理

每 6 小时自动巡检 QQ 音乐活动页 →提取免费活动信息 → 与上次快照对比 → 有新活动则推送到微信

## 文件说明

- `monitor.py` - 核心监控脚本
- `.github/workflows/monitor.yml` - GitHub Actions 定时任务配置