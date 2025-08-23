<<<<<<< HEAD
# 抽老婆
AstrBot 插件
版本1.0.3（beta03）  
从QQ群里抽取一个群友当老婆

灵感来源：[抽群友](https://github.com/tenno1174/astrbot-plugin-chouqunyou)
# 命令列表
## 用户命令
`/今日老婆`抽取并@随机群友  
`/今日记录`查询今日记录  
# 更多
欢迎来QQ群 <u>[964447137](https://qm.qq.com/q/WzQsmjbN0A)</u> 玩哦  
作者网站在这 <u>[玖帕喵](https://jupamiao.asia)</u>  
~~另外一个 <u>[玖帕喵](https://jupamiao.github.io)</u>~~
# 支持

[帮助文档](https://astrbot.app)
=======
# AstrBot 抽老婆插件

![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)
![License](https://img.shields.io/github/license/nuomicici/astrbot-plugin-choulaopo)
![Version](https://img.shields.io/badge/version-1.0.4-green)

## 🌟 插件简介

本插件为 **AstrBot** 提供 `/今日老婆` 等命令，可在QQ群中随机抽取一位群友作为“今日老婆”，并支持每日抽取次数限制、记录查询等功能。  
灵感来源：[抽群友](https://github.com/tenno1174/astrbot_plugin_chouqunyou)

---

## ✨ 主要特性

* **支持 aiocqhttp.QQ 平台**
* **每日抽取次数限制**（可配置）
* **自动每日重置**
* **抽取结果可@对方或仅显示昵称**
* **支持查询今日抽取记录**
* **简单易用的命令体系**

---

## 📋 命令列表

### 用户命令

| 命令                | 说明                       |
|---------------------|----------------------------|
| `/今日老婆`         | 抽取并@随机群友            |
| `/今日老婆-@`       | 抽取但不@对方，仅显示昵称  |
| `/今日记录`         | 查询今日抽取记录           |
| `/帮助`             | 查看帮助信息               |

---

## 🚀 安装与使用

### 方法一：插件市场安装（推荐）

在 **AstrBot 插件市场** 搜索 **AstrBot_抽老婆** 并一键安装。

### 方法二：手动安装

```bash
cd AstrBot/data/plugins
git clone https://github.com/nuomicici/astrbot-plugin-choulaopo.git
```

---

## 🛠️ 配置说明

插件首次运行会自动生成 `choulaopo_config.json` 配置文件，可手动修改每日抽取上限：

```json
{
  "draw_limit": 3
}
```

---

## 📖 使用示例

```bash
/今日老婆
/今日老婆-@
/今日记录
/帮助
```

---

## 💬 更多交流

欢迎加入QQ群 <u>[964447137](https://qm.qq.com/q/WzQsmjbN0A)</u> 交流反馈。

作者网站：<u>[玖帕喵](https://jupamiao.asia)</u>  
~~备用站点：<u>[玖帕喵](https://jupamiao.github.io)</u>~~

---

## 📄 许可证

本项目采用 **MIT** 许可证 - 详情请参阅 [LICENSE](LICENSE)。

---

## 🙏 致谢

* [AstrBot](https://github.com/AstrBotDevs/AstrBot) — 高性能聊天机器人框架
* [抽群友](https://github.com/tenno1174/astrbot_plugin_chouqunyou) — 灵感来源
>>>>>>> 6e45925 (优化了一些代码)
