import os
import json
import random
from datetime import datetime
from typing import List, Dict, Any

# 根据官方文档和参考插件导入必要的AstrBot API
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.message_components as Comp

# 根据官方文档：开发者必须使用@register装饰器来注册插件，这是AstrBot识别和加载插件的必要条件
@register("抽老婆", "糯米茨", "随机抽老婆插件 - 每日抽取群友作为老婆", "v2.0.2", "https://github.com/astrbot-plugin-choulaopo")
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
    def __init__(self, context: Context, config: AstrBotConfig):
        """
        插件初始化方法
        根据官方文档：在__init__方法中会传入Context对象
        """
        super().__init__(context)
        self.config = config
        
        # 插件数据目录，建议使用一个固定的英文名
        self.data_dir = os.path.join("data", "plugins", "random_wife")
        self.records_file = os.path.join(self.data_dir, "wife_records.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.records = self._load_records()
        logger.info("随机抽老婆插件已加载")
        
    def _load_records(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"date": "", "groups": {}}
        except Exception as e:
            logger.error(f"加载记录文件失败: {e}")
            return {"date": "", "groups": {}}
    
    def _save_records(self):
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记录文件失败: {e}")
    
    def _is_new_day(self) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.records.get("date") != today
    
    def _reset_daily_records(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.records = {"date": today, "groups": {}}
        self._save_records()
        logger.info("每日抽取记录已重置")
    
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
    
    def _get_today_count(self, group_id: str, user_id: str) -> int:
        if self._is_new_day():
            self._reset_daily_records()
            return 0
        
        group_records = self.records.get("groups", {}).get(group_id, {}).get("records", [])
        return sum(1 for record in group_records if record["user_id"] == user_id)
    
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
    
    @filter.command("今日老婆", alias={'抽老婆'})
    async def draw_wife_with_at(self, event: AstrMessageEvent):
        """抽取今日老婆（带@功能）"""
        async for result in self._draw_wife_common(event, with_at=True):
            yield result
    
    @filter.command("抽老婆-@",alias={'今日老婆-@'})
    async def draw_wife_without_at(self, event: AstrMessageEvent):
        """抽取今日老婆（不带@功能）"""
        async for result in self._draw_wife_common(event, with_at=False):
            yield result
    
    async def _draw_wife_common(self, event: AstrMessageEvent, with_at: bool):
        """抽取老婆的通用方法"""
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
    
    @filter.command("我的老婆", "抽取历史")
    async def show_my_wives(self, event: AstrMessageEvent):
        """显示用户的抽取历史"""
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
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("重置记录")
    async def reset_records(self, event: AstrMessageEvent):
        self._reset_daily_records()
        yield event.plain_result("今日抽取记录已重置！")
    
    @filter.command("抽老婆帮助", "老婆插件帮助")
    async def show_help(self, event: AstrMessageEvent):
        daily_limit = self.config.get("daily_limit", 3)
        excluded_count = len(self.config.get("excluded_users", []))
        help_text = f"""=== 抽老婆插件帮助 v1.3.4 ===
        
🎯 主要功能：
• 今日老婆 / 抽老婆 - 随机抽取群友作为今日老婆（带头像和@）
• 抽老婆-@ - 随机抽取群友（带头像，不带@）
• 我的老婆 / 抽取历史 - 查看今天的抽取记录
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
    
    async def terminate(self):
        try:
            self._save_records()
            logger.info("抽老婆插件资源已清理完毕")
        except Exception as e:
            logger.error(f"插件终止时出现错误: {e}")
