import os
import json
import random
from datetime import datetime
from typing import List, Dict, Any

# 根据官方文档和参考插件导入必要的AstrBot API
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.message_components as Comp

# 根据官方文档：开发者必须使用@register装饰器来注册插件，这是AstrBot识别和加载插件的必要条件
@register("抽老婆", "糯米茨", "随机抽老婆插件 - 每日抽取群友作为老婆", "v1.2.0", "https://github.com/your-repo")
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
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        """
        插件初始化方法
        根据官方文档：在__init__方法中会传入Context对象和config对象
        """
        super().__init__(context)
        self.config = config  # 根据官方文档：AstrBotConfig继承自Dict，拥有字典的所有方法
        
        # 根据官方文档插件开发原则：持久化数据请存储于data目录下，而非插件自身目录
        self.data_dir = os.path.join("data", "plugins", "random_wife")
        self.records_file = os.path.join(self.data_dir, "wife_records.json")
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载抽取记录
        self.records = self._load_records()
        
        # 根据官方文档：请务必使用from astrbot.api import logger来获取日志对象
        logger.info("随机抽老婆插件已加载")
        
    def _load_records(self) -> Dict[str, Any]:
        """
        加载抽取记录
        记录格式：{
            "date": "2024-01-01",
            "groups": {
                "group_id": {
                    "records": [
                        {
                            "user_id": "发起者QQ号",
                            "wife_id": "被抽中的QQ号", 
                            "wife_name": "被抽中用户昵称",
                            "timestamp": "时间戳",
                            "with_at": true
                        }
                    ]
                }
            }
        }
        """
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    return records
            else:
                return {"date": "", "groups": {}}
        except Exception as e:
            logger.error(f"加载记录文件失败: {e}")
            return {"date": "", "groups": {}}
    
    def _save_records(self):
        """保存抽取记录到JSON文件"""
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记录文件失败: {e}")
    
    def _is_new_day(self) -> bool:
        """检查是否是新的一天，需要重置记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.records.get("date") != today
    
    def _reset_daily_records(self):
        """重置每日记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.records = {
            "date": today,
            "groups": {}
        }
        self._save_records()
        logger.info("每日抽取记录已重置")
    
    async def _get_group_members(self, event: AstrMessageEvent) -> List[Dict[str, Any]]:
        """
        获取群组成员列表
        基于参考插件的实现，使用aiocqhttp协议端API获取群成员列表
        """
        try:
            group_id = event.get_group_id()
            if not group_id:
                logger.warning("无法获取群组ID")
                return []
            
            # 根据参考插件：检查是否为aiocqhttp平台
            if event.get_platform_name() == "aiocqhttp":
                # 根据参考插件：断言为AiocqhttpMessageEvent类型
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot  # 得到client
                payloads = {
                    "group_id": group_id,
                    "no_cache": True
                }
                # 根据参考插件：调用协议端API获取群成员列表
                ret = await client.api.call_action('get_group_member_list', **payloads)
                return ret
            else:
                logger.warning(f"不支持的平台: {event.get_platform_name()}")
                return []
                
        except Exception as e:
            logger.error(f"获取群成员失败: {e}")
            return []
    
    def _get_today_count(self, group_id: str, user_id: str) -> int:
        """获取用户今日在指定群的抽取次数"""
        if self._is_new_day():
            self._reset_daily_records()
            return 0
        
        group_records = self.records.get("groups", {}).get(group_id, {}).get("records", [])
        count = sum(1 for record in group_records if record["user_id"] == user_id)
        return count
    
    def _add_record(self, group_id: str, user_id: str, wife_id: str, wife_name: str, with_at: bool):
        """添加抽取记录"""
        if self._is_new_day():
            self._reset_daily_records()
        
        # 确保群组记录存在
        if group_id not in self.records["groups"]:
            self.records["groups"][group_id] = {"records": []}
        
        # 添加新记录
        record = {
            "user_id": user_id,
            "wife_id": wife_id,
            "wife_name": wife_name,
            "timestamp": datetime.now().isoformat(),
            "with_at": with_at
        }
        
        self.records["groups"][group_id]["records"].append(record)
        self._save_records()
        logger.info(f"用户{user_id}在群{group_id}抽取了{wife_name}({wife_id})")
    
    # 根据官方文档：使用@filter.command装饰器注册指令
    @filter.command("今日老婆", "抽老婆")
    async def draw_wife_with_at(self, event: AstrMessageEvent):
        """
        抽取今日老婆（带@功能）
        """
        await self._draw_wife_common(event, with_at=True)
    
    @filter.command("抽老婆-@","今日老婆-@")
    async def draw_wife_without_at(self, event: AstrMessageEvent):
        """
        抽取今日老婆（不带@功能）
        """
        await self._draw_wife_common(event, with_at=False)
    
    async def _draw_wife_common(self, event: AstrMessageEvent, with_at: bool):
        """
        抽取老婆的通用方法
        根据文档：使用AstrMessageEvent获取消息信息和发送回复
        """
        # 根据文档：使用is_private_chat()方法判断是否为私聊
        if event.is_private_chat():
            yield event.plain_result("抽老婆功能仅在群聊中可用哦~")
            return
        
        # 根据文档：使用相应方法获取用户和群组信息
        user_id = event.get_sender_id()  # 获取发送者ID
        group_id = event.get_group_id()  # 获取群组ID
        user_name = event.get_sender_name()  # 获取发送者昵称
        bot_id = event.get_self_id()  # 获取Bot自身ID
        
        if not group_id:
            yield event.plain_result("无法获取群组信息")
            return
        
        # 检查今日抽取次数
        today_count = self._get_today_count(group_id, user_id)
        daily_limit = self.config.get("daily_limit", 3)  # 从配置文件获取每日限制次数
        
        if today_count >= daily_limit:
            yield event.plain_result(f"你今天已经抽了{today_count}次老婆了，明天再来吧！")
            return
        
        # 获取群成员列表
        members = await self._get_group_members(event)
        
        # 如果无法获取群成员，提示用户
        if not members:
            yield event.plain_result("暂时无法获取群成员列表，请确保Bot有相应权限，或当前平台不支持此功能")
            return
        
        # 过滤排除的用户
        excluded = set(str(uid) for uid in self.config.get("excluded_users", []))  # 从配置文件获取排除用户列表，转换为字符串
        excluded.add(str(bot_id))  # 排除Bot自身
        excluded.add(str(user_id))  # 排除发起者自己
        
        # 根据参考插件的数据结构过滤成员
        available_members = [
            member for member in members 
            if str(member.get("user_id", "")) not in excluded
        ]
        
        if not available_members:
            yield event.plain_result("群里没有可以抽取的成员哦~")
            return
        
        # 根据参考插件：随机抽取一个群友
        wife = random.choice(available_members)
        wife_id = wife.get("user_id")
        wife_name = wife.get("nickname", f"用户{wife_id}")
        
        # 记录抽取结果
        self._add_record(group_id, user_id, str(wife_id), wife_name, with_at)
        
        # 构造回复消息
        remaining = daily_limit - today_count - 1
        
        if with_at:
            # 根据参考插件：使用chain_result创建消息链结果
            # 构造包含@的消息链
            chain = [
                Comp.At(qq=user_id),  # @发起者
                Comp.Plain(" 你的今日老婆是："),
                Comp.At(qq=wife_id),  # @被抽中的用户
                Comp.Plain(f" {wife_name}！\n剩余抽取次数：{remaining}次")
            ]
            yield event.chain_result(chain)
        else:
            # 根据文档：使用plain_result创建文本消息结果
            result_text = f"{user_name if user_name else user_id} 今日老婆是：{wife_name}！\n剩余抽取次数：{remaining}次"
            yield event.plain_result(result_text)
    
    @filter.command("我的老婆", "抽取历史")
    async def show_my_wives(self, event: AstrMessageEvent):
        """显示用户的抽取历史"""
        # 检查是否为群聊
        if event.is_private_chat():
            yield event.plain_result("此功能仅在群聊中可用")
            return
        
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        if not group_id:
            yield event.plain_result("无法获取群组信息")
            return
        
        # 检查今日是否有记录
        if self._is_new_day():
            self._reset_daily_records()
        
        group_records = self.records.get("groups", {}).get(group_id, {}).get("records", [])
        user_records = [record for record in group_records if record["user_id"] == user_id]
        
        if not user_records:
            yield event.plain_result("你今天还没有抽过老婆哦~")
            return
        
        # 构造历史记录消息
        daily_limit = self.config.get("daily_limit", 3)
        result_text = f"你今天的老婆记录({len(user_records)}/{daily_limit})：\n"
        
        for i, record in enumerate(user_records, 1):
            time_str = datetime.fromisoformat(record["timestamp"]).strftime("%H:%M:%S")
            at_status = "(@)" if record.get("with_at", False) else ""
            result_text += f"{i}. {record['wife_name']} ({time_str}){at_status}\n"
        
        remaining = daily_limit - len(user_records)
        result_text += f"剩余次数：{remaining}次"
        
        yield event.plain_result(result_text)
    
    # 根据文档：使用@filter.permission_type限制管理员权限
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("重置记录")
    async def reset_records(self, event: AstrMessageEvent):
        """
        管理员重置抽取记录
        根据文档：使用@filter.permission_type(filter.PermissionType.ADMIN)限制仅管理员可用
        """
        # 重置记录
        self._reset_daily_records()
        yield event.plain_result("今日抽取记录已重置！")
    
    @filter.command("抽老婆帮助", "老婆插件帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示插件帮助菜单"""
        daily_limit = self.config.get("daily_limit", 3)
        excluded_count = len(self.config.get("excluded_users", []))
        
        help_text = f"""=== 抽老婆插件帮助 ===
        
🎯 主要功能：
• 今日老婆 / 抽老婆 - 随机抽取群友作为今日老婆（带@）
• 抽老婆-@ - 随机抽取群友作为今日老婆（不带@）
• 我的老婆 / 抽取历史 - 查看今天的抽取记录
• 重置记录 - 管理员专用，重置今日记录

📝 使用说明：
• 每人每日可抽取 {daily_limit} 次
• 自动排除Bot和发起者本人
• 每日0点自动重置记录
• 支持@和不@两种模式
• 仅支持aiocqhttp平台

⚙️ 当前配置：
• 每日限制：{daily_limit} 次
• 排除用户：{excluded_count} 个

💡 提示：插件数据保存在data目录下，支持持久化存储"""
        
        yield event.plain_result(help_text)
    
    async def terminate(self):
        """
        插件终止方法
        根据文档：该方法为基类提供的抽象方法，必须在插件中实现
        用于插件禁用、重载或关闭AstrBot时触发，用于释放插件资源
        """
        try:
            # 保存最新的记录
            self._save_records()
            logger.info("抽老婆插件资源已清理完毕")
        except Exception as e:
            logger.error(f"插件终止时出现错误: {e}")