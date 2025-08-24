import os
import json
import random
from datetime import datetime
from typing import List, Dict, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.message_components as Comp

@register("抽老婆", "糯米茨", "随机抽老婆插件 - 每日抽取群友作为老婆", "v2.0", "https://github.com/astrbot-plugin-choulaopo")
class RandomWifePlugin(Star):
    """
    AstrBot随机抽老婆插件
    功能：
    1. 随机抽取群友作为"老婆"（排除Bot和指定用户）
    2. 支持每日抽取次数限制（可配置）
    3. 持久化保存抽取记录到JSON文件
    4. 支持@和不@的命令选项
    5. 查看历史记录功能
    6. 管理员重置记录功能
    7. 帮助菜单
    8. 输出被抽中成员的头像
    """
    # 初始化插件，设置配置、数据目录并加载历史记录
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        self.data_dir = os.path.join("data", "plugins", "random_wife")
        self.records_file = os.path.join(self.data_dir, "wife_records.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.records = self._load_records()
        logger.info("随机抽老婆插件已加载")
        
    # 从JSON文件加载抽取记录，如果文件不存在或加载失败则返回一个空的记录结构
    def _load_records(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"date": "", "groups": {}}
        except Exception as e:
            logger.error(f"加载记录文件失败: {e}")
            return {"date": "", "groups": {}}
    
    # 将当前的抽取记录以JSON格式保存到文件中
    def _save_records(self):
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记录文件失败: {e}")
    
    # 检查当前日期是否与记录中的日期不同，用于判断是否是新的一天
    def _is_new_day(self) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.records.get("date") != today
    
    # 重置每日的抽取记录，将日期更新为今天并清空所有群组的抽取数据
    def _reset_daily_records(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.records = {"date": today, "groups": {}}
        self._save_records()
        logger.info("每日抽取记录已重置")
    
    # 异步获取事件所在群组的成员列表，目前仅支持aiocqhttp平台
    async def _get_group_members(self, event: AstrMessageEvent) -> List[Dict[str, Any]]:
        try:
            group_id = event.get_group_id()
            if not group_id:
                logger.warning("无法获取群组ID")
                return []
            
            if event.get_platform_name() == "aiocqhttp":
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot
                payloads = {"group_id": group_id, "no_cache": True}
                return await client.api.call_action('get_group_member_list', **payloads)
            else:
                logger.warning(f"不支持的平台: {event.get_platform_name()}")
                return []
        except Exception as e:
            logger.error(f"获取群成员失败: {e}")
            return []
    
    # 获取指定用户在指定群组今天的已抽取次数，如果跨天则会自动重置记录
    def _get_today_count(self, group_id: str, user_id: str) -> int:
        if self._is_new_day():
            self._reset_daily_records()
            return 0
        
        group_records = self.records.get("groups", {}).get(group_id, {}).get("records", [])
        return sum(1 for record in group_records if record["user_id"] == user_id)
    
    # 新增一条抽取记录，包含用户ID、老婆ID、老婆昵称、时间戳和是否@了对方
    def _add_record(self, group_id: str, user_id: str, wife_id: str, wife_name: str, with_at: bool):
        if self._is_new_day():
            self._reset_daily_records()
        
        if group_id not in self.records["groups"]:
            self.records["groups"][group_id] = {"records": []}
        
        record = {
            "user_id": user_id, "wife_id": wife_id, "wife_name": wife_name,
            "timestamp": datetime.now().isoformat(), "with_at": with_at
        }
        self.records["groups"][group_id]["records"].append(record)
        self._save_records()
        logger.info(f"用户{user_id}在群{group_id}抽取了{wife_name}({wife_id})")
    
    # 处理“今日老婆”和“抽老婆”命令，调用通用抽取方法并启用@功能
    @filter.command("今日老婆", "抽老婆")
    async def draw_wife_with_at(self, event: AstrMessageEvent):
        async for result in self._draw_wife_common(event, with_at=True):
            yield result
    
    # 处理“抽老婆-@”和“今日老婆-@”命令，调用通用抽取方法并禁用@功能
    @filter.command("抽老婆-@", "今日老婆-@")
    async def draw_wife_without_at(self, event: AstrMessageEvent):
        async for result in self._draw_wife_common(event, with_at=False):
            yield result
    
    # 抽取老婆的核心通用逻辑，处理包括环境检查、次数限制、成员获取、随机选择和结果发送等步骤
    async def _draw_wife_common(self, event: AstrMessageEvent, with_at: bool):
        if event.is_private_chat():
            yield event.plain_result("抽老婆功能仅在群聊中可用哦~")
            return
        
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        bot_id = event.get_self_id()
        
        if not group_id:
            yield event.plain_result("无法获取群组信息")
            return
        
        daily_limit = self.config.get("daily_limit", 3)
        today_count = self._get_today_count(group_id, user_id)
        if today_count >= daily_limit:
            yield event.plain_result(f"你今天已经抽了{today_count}次老婆了，明天再来吧！")
            return
        
        members = await self._get_group_members(event)
        if not members:
            yield event.plain_result("暂时无法获取群成员列表，请确保Bot有相应权限")
            return
        
        excluded = {str(uid) for uid in self.config.get("excluded_users", [])}
        excluded.add(str(bot_id))
        excluded.add(str(user_id))
        
        available_members = [m for m in members if str(m.get("user_id", "")) not in excluded]
        if not available_members:
            yield event.plain_result("群里没有可以抽取的成员哦~")
            return
        
        wife = random.choice(available_members)
        wife_id, wife_name = wife.get("user_id"), wife.get("card") or wife.get("nickname") or f"用户{wife.get('user_id')}"
        
        self._add_record(group_id, user_id, str(wife_id), wife_name, with_at)
        
        avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={wife_id}&spec=640"
        remaining = daily_limit - today_count - 1
        
        chain = [Comp.At(qq=user_id), Comp.Plain(" 你的今日老婆是：\n"), Comp.Image.fromURL(avatar_url)]
        if with_at:
            chain.extend([Comp.Plain("\n"), Comp.At(qq=wife_id), Comp.Plain(f" {wife_name}")])
        else:
            chain.append(Comp.Plain(f"\n{wife_name}"))
        chain.append(Comp.Plain(f"\n剩余抽取次数：{remaining}次"))

        yield event.chain_result(chain)
    
    # 处理“我的老婆”和“抽取历史”命令，显示用户当天的抽取记录列表
    @filter.command("我的老婆", "抽取历史")
    async def show_my_wives(self, event: AstrMessageEvent):
        if event.is_private_chat():
            yield event.plain_result("此功能仅在群聊中可用")
            return
        
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            yield event.plain_result("无法获取群组信息")
            return
        
        if self._is_new_day():
            self._reset_daily_records()
        
        group_records = self.records.get("groups", {}).get(group_id, {}).get("records", [])
        user_records = [r for r in group_records if r["user_id"] == user_id]
        
        if not user_records:
            yield event.plain_result("你今天还没有抽过老婆哦~")
            return
        
        daily_limit = self.config.get("daily_limit", 3)
        result = [f"你今天的老婆记录({len(user_records)}/{daily_limit})："]
        for i, record in enumerate(user_records, 1):
            time_str = datetime.fromisoformat(record["timestamp"]).strftime("%H:%M:%S")
            at_status = "(@)" if record.get("with_at", False) else ""
            result.append(f"{i}. {record['wife_name']} ({record['wife_id']}) 在 {time_str} {at_status}")
        
        remaining = daily_limit - len(user_records)
        result.append(f"剩余次数：{remaining}次")
        yield event.plain_result("\n".join(result))
    
    # 处理“重置记录”命令，仅管理员可用，用于手动清空当天的所有抽取记录
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("重置记录")
    async def reset_records(self, event: AstrMessageEvent):
        self._reset_daily_records()
        yield event.plain_result("今日抽取记录已重置！")
    
    # 处理“抽老婆帮助”和“老婆插件帮助”命令，显示插件的功能、命令、说明和当前配置
    @filter.command("抽老婆帮助", "老婆插件帮助")
    async def show_help(self, event: AstrMessageEvent):
        daily_limit = self.config.get("daily_limit", 3)
        excluded_count = len(self.config.get("excluded_users", []))
        help_text = f"""=== 抽老婆插件帮助 v1.3.4 ===
        
🎯 主要功能：
• 今日老婆 / 抽老婆 - 随机抽取群友作为今日老婆。可直接在命令后添加“-@”选择不@抽取（不要添加空格！）
• 重置记录 - 管理员专用，重置今日记录

📝 使用说明：
• 每人每日可抽取 {daily_limit} 次
• 结果会附带被抽中成员的头像
• 自动排除Bot和发起者本人
• 每日0点自动重置记录
• 仅支持aiocqhttp平台

⚙️ 当前配置：
• 每日限制：{daily_limit} 次
• 排除用户：{excluded_count} 个

💡 提示：插件数据保存在data目录下，支持持久化存储"""
        yield event.plain_result(help_text)
    
    # 在插件终止时调用，确保将最新的记录保存到文件，防止数据丢失
    async def terminate(self):
        try:
            self._save_records()
            logger.info("抽老婆插件资源已清理完毕")
        except Exception as e:
            logger.error(f"插件终止时出现错误: {e}")