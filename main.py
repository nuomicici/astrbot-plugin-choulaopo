import random
from datetime import datetime

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.message.components import At, Image, Plain
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.star_tools import StarTools

from .data import WifeRecord, WifeRecordStore
from .utils import HELP_TEXT_TEMPLATE, get_ats, get_group_members


class RandomWifePlugin(Star):
    """
    随机抽老婆插件
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.cfg = config
        self.daily_limit = config["daily_limit"]
        self.excluded_users = self.excluded_users = {
            str(u) for u in config.get("excluded_users", [])
        }

        self.data_dir = StarTools.get_data_dir()
        self.store = WifeRecordStore(self.data_dir)

    async def terminate(self):
        self.store.save()

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.command("抽老婆", alias={"今日老婆"})
    async def wife_smacking(self, event: AiocqhttpMessageEvent):
        """从群里随机抽取一位老婆"""
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        bot_id = event.get_self_id()
        at_ids = get_ats(event)
        today_count = self.store.get_user_today_count(group_id, user_id)

        if today_count >= self.daily_limit:
            yield event.plain_result(
                f"你今天已经抽了 {today_count} 次老婆了，明天再来吧！"
            )
            return

        members = await get_group_members(event)
        if not members:
            yield event.plain_result("无法获取群成员列表")
            return

        excluded = self.excluded_users | {bot_id, user_id}
        candidates = [m for m in members if str(m.get("user_id")) not in excluded]

        if not candidates:
            yield event.plain_result("群里没有可以抽取的成员哦~")
            return

        wife = random.choice(candidates)
        wife_id = str(wife["user_id"])
        wife_name = wife.get("card") or wife.get("nickname") or f"用户({wife_id})"

        record = WifeRecord(
            user_id=str(user_id),
            wife_id=wife_id,
            wife_name=wife_name,
            timestamp=datetime.now(),
        )

        self.store.add_record(group_id, record)

        remaining = self.daily_limit - today_count - 1
        avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={wife_id}&spec=640"

        chain = [
            At(qq=user_id),
            Plain(" 你的今日老婆是：\n"),
            Image.fromURL(avatar_url),
        ]

        if at_ids:
            chain.extend(
                [
                    At(qq=wife_id),
                    Plain(f"\n剩余抽取次数：{remaining}次"),
                ]
            )
        else:
            chain.append(Plain(f"\n{wife_name}\n剩余抽取次数：{remaining}次"))

        yield event.chain_result(chain)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.command("我的老婆", alias={"抽取历史"})
    async def show_my_wives(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        records = self.store.list_user_records(group_id, user_id)
        if not records:
            yield event.plain_result("你今天还没有抽过老婆哦~")
            return

        lines = [f"你今天的老婆记录 ({len(records)}/{self.daily_limit})："]

        for i, record in enumerate(records, 1):
            time_str = record.timestamp.strftime("%H:%M:%S")
            lines.append(f"{i}. {record.wife_name} ({record.wife_id}) {time_str}")

        lines.append(f"剩余次数：{self.daily_limit - len(records)}次")
        yield event.plain_result("\n".join(lines))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("重置记录")
    async def reset_records(self, event: AstrMessageEvent):
        """重置今日抽取老婆的记录"""
        self.store.reset_today()
        yield event.plain_result("今日抽取记录已重置！")

    @filter.command("抽老婆帮助", alias={"今日老婆帮助"})
    async def show_help(self, event: AstrMessageEvent):
        """显示抽老婆帮助"""
        help_text = HELP_TEXT_TEMPLATE.format(
            daily_limit=self.daily_limit,
            excluded_count=len(self.excluded_users),
        )

        yield event.plain_result(help_text)
