import json
import os
import random
from datetime import datetime, date
from typing import List, Optional
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, MessageType
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.message_components as Comp

@register("choulaopo", "糯米茨", "随机群友抽取插件", "1.2.0")
class RandomWifeStar(Star):
    """随机群友抽取插件"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 插件配置
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.plugin_dir, "config.json")
        self.data_file = os.path.join(self.plugin_dir, "daily_records.json")
        
        # 默认配置
        self.default_config = {
            "daily_limit": 3,  # 每日抽取次数上限
            "excluded_qq": [],  # 排除的QQ号列表
            "enable_at": True   # 是否启用@功能
        }
        
        # 加载配置
        self.config = self.load_config()
        
        # 确保数据文件存在
        self.ensure_data_file()
    
    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                # 创建默认配置文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.default_config, f, ensure_ascii=False, indent=2)
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.default_config.copy()
    
    def ensure_data_file(self):
        """确保数据文件存在"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def load_daily_records(self) -> dict:
        """加载每日记录"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_daily_records(self, records: dict):
        """保存每日记录"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记录失败: {e}")
    
    def get_today_key(self) -> str:
        """获取今天的日期键"""
        return date.today().strftime("%Y-%m-%d")
    
    def clean_old_records(self, records: dict) -> dict:
        """清理旧记录，只保留今天的"""
        today = self.get_today_key()
        return {today: records.get(today, {})} if today in records else {}
    
    async def get_group_members(self, event: AstrMessageEvent) -> List[dict]:
        """获取群成员列表"""
        try:
            group_id = event.get_group_id()
            if not group_id:
                return []
            
            # 仅支持aiocqhttp平台
            if event.get_platform_name() == "aiocqhttp":
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot
                payloads = {
                    "group_id": group_id,
                    "no_cache": True
                }
                ret = await client.api.call_action('get_group_member_list', **payloads)
                return ret if ret else []
            else:
                logger.warning(f"暂不支持平台: {event.get_platform_name()}")
                return []
        except Exception as e:
            logger.error(f"获取群成员列表失败: {e}")
            return []
    
    @filter.command("今日老婆", "抽老婆")
    async def draw_wife(self, event: AstrMessageEvent):
        """抽取今日老婆"""
        # 只在群聊中有效
        if event.get_message_type() != MessageType.GROUP_MESSAGE:
            yield event.plain_result("此功能仅在群聊中可用哦~")
            return
        
        # 获取群ID和用户ID
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        bot_id = event.get_self_id()
        
        if not group_id:
            yield event.plain_result("获取群信息失败")
            return
        
        # 加载今日记录
        records = self.load_daily_records()
        today = self.get_today_key()
        
        # 清理旧记录
        records = self.clean_old_records(records)
        
        # 初始化今日记录
        if today not in records:
            records[today] = {}
        
        today_records = records[today]
        
        # 检查该用户今日抽取次数
        user_draws = today_records.get(user_id, [])
        if len(user_draws) >= self.config["daily_limit"]:
            yield event.plain_result(f"你今天已经抽取了 {len(user_draws)} 次，达到每日上限啦~\n可使用「我的老婆」查看抽取历史")
            return
        
        # 获取群成员列表
        group_members = await self.get_group_members(event)
        
        if not group_members:
            yield event.plain_result("获取群成员列表失败，请稍后重试")
            return
        
        # 过滤排除的用户
        excluded_users = set(self.config["excluded_qq"] + [bot_id, user_id])
        available_members = [member for member in group_members 
                           if member.get("user_id") not in excluded_users]
        
        if not available_members:
            yield event.plain_result("没有可抽取的群友哦~")
            return
        
        # 随机抽取
        selected_member = random.choice(available_members)
        target_id = selected_member.get("user_id")
        target_name = selected_member.get("nickname", f"群友{target_id}")
        
        # 记录抽取结果
        draw_result = {
            "target_id": str(target_id),
            "target_name": target_name,
            "timestamp": datetime.now().isoformat(),
            "with_at": self.config.get("enable_at", True)
        }
        
        user_draws.append(draw_result)
        today_records[user_id] = user_draws
        records[today] = today_records
        
        # 保存记录
        self.save_daily_records(records)
        
        # 构建消息链
        chain = [
            Comp.At(qq=user_id),  # @发送者
            Comp.Plain(f" 🎲 你今天的老婆是：{target_name}\n抽取次数：{len(user_draws)}/{self.config['daily_limit']}")
        ]
        
        # 添加头像
        avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={target_id}&spec=640"
        chain.append(Comp.Image.fromURL(avatar_url))
        
        # 是否@被抽中的用户
        if self.config.get("enable_at", True):
            chain.extend([
                Comp.Plain("\n恭喜 "),
                Comp.At(qq=target_id),
                Comp.Plain(" 被抽中！")
            ])
        
        yield event.chain_result(chain)
    
    @filter.command("我的老婆", "抽取历史")
    async def my_history(self, event: AstrMessageEvent):
        """查看抽取历史"""
        user_id = event.get_sender_id()
        
        # 加载记录
        records = self.load_daily_records()
        today = self.get_today_key()
        
        if today not in records or user_id not in records[today]:
            yield event.plain_result("你今天还没有抽取过老婆哦~\n使用「今日老婆」命令开始抽取吧！")
            return
        
        user_draws = records[today][user_id]
        
        result_text = f"📋 你今日的抽取历史\n"
        result_text += f"抽取次数：{len(user_draws)}/{self.config['daily_limit']}\n\n"
        
        for i, draw in enumerate(user_draws, 1):
            timestamp = datetime.fromisoformat(draw["timestamp"])
            time_str = timestamp.strftime("%H:%M:%S")
            result_text += f"{i}. {draw['target_name']} ({time_str})\n"
        
        if len(user_draws) < self.config['daily_limit']:
            result_text += f"\n还可以抽取 {self.config['daily_limit'] - len(user_draws)} 次哦~"
        
        yield event.plain_result(result_text)
    
    @filter.command("重置记录")
    async def reset_records(self, event: AstrMessageEvent):
        """重置记录（仅管理员可用）"""
        # 检查是否为管理员
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令~")
            return
        
        # 清空今日记录
        records = self.load_daily_records()
        today = self.get_today_key()
        
        if today in records and records[today]:
            records[today] = {}
            self.save_daily_records(records)
            yield event.plain_result("✅ 今日抽取记录已重置")
        else:
            yield event.plain_result("今日暂无抽取记录")
    
    @filter.command("抽老婆帮助", "老婆插件帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示插件帮助"""
        help_text = """🎲 随机群友抽取插件帮助

📝 可用命令：
• 今日老婆 / 抽老婆 - 随机抽取一个群友
• 我的老婆 / 抽取历史 - 查看今日抽取历史  
• 重置记录 - 清空今日记录（管理员专用）
• 抽老婆帮助 - 显示此帮助信息

⚙️ 插件设置：
• 每日抽取上限：{} 次
• 排除用户：{} 个
• @功能：{}

📋 说明：
• 仅在群聊中可用
• 不会抽到自己和bot
• 每日0点自动重置记录
• 可通过配置文件修改设置
• 目前仅支持aiocqhttp平台""".format(
            self.config["daily_limit"],
            len(self.config["excluded_qq"]),
            "开启" if self.config["enable_at"] else "关闭"
        )
        
        yield event.plain_result(help_text)
    
    async def terminate(self):
        """插件终止时的清理工作"""
        pass
