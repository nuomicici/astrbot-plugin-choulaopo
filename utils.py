
from astrbot.api import logger
from astrbot.core.message.components import At
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

# help_text.py

HELP_TEXT_TEMPLATE = """=== 抽老婆帮助  ===

🎯 主要功能：
• 今日老婆 / 抽老婆 - 随机抽取群友作为今日老婆（带@）
• 抽老婆-@ / 今日老婆-@
   - 随机抽取群友（不带@）
• 我的老婆 / 抽取历史
   - 查看今天的抽取记录
• 重置记录
   - 管理员专用，重置今日记录
• 抽老婆帮助 / 今日老婆帮助
   - 查看该帮助

📝 使用说明：
• 每人每日可抽取 {daily_limit} 次
• 结果会附带被抽中成员的头像
• 自动排除 Bot 和发起者本人
• 每日 0 点自动重置记录

⚙️ 当前配置：
• 每日限制：{daily_limit} 次
• 排除用户：{excluded_count} 个
"""


async def get_group_members(event: AiocqhttpMessageEvent) -> list[dict]:
    try:
        group_id = event.get_group_id()
        return await event.bot.get_group_member_list(group_id=group_id)  # type: ignore
    except Exception as e:
        logger.error(f"获取群成员失败: {e}")
        return []


def get_ats(event: AiocqhttpMessageEvent) -> list[str]:
    """获取被at者们的id列表,(@增强版)"""
    ats = [str(seg.qq) for seg in event.get_messages()[1:] if isinstance(seg, At)]
    for arg in event.message_str.split(" "):
        if arg.startswith("@") and arg[1:].isdigit():
            ats.append(arg[1:])
    return ats

