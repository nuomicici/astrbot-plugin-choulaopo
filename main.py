from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests
import json
import random
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.message_components as Comp
import datetime
import asyncio
import os

# 常量定义
CONFIG_PATH = "choulaopo_config.json"
DEFAULT_DRAW_LIMIT = 3
AVATAR_URL_TEMPLATE = "https://q4.qlogo.cn/headimg_dl?dst_uin={}&spec=640"
RESET_HOUR = 0  # 凌晨0点重置

# 全局变量
daily_records = {}
daily_counts = {}

class ConfigManager:
    """配置管理器，负责加载、保存和管理插件配置"""
    
    def __init__(self, path):
        self.path = path
        self.config = self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 配置验证
                    if not isinstance(config.get("draw_limit"), int) or config["draw_limit"] < 1:
                        logger.warning("配置文件中的draw_limit无效，使用默认值")
                        config["draw_limit"] = DEFAULT_DRAW_LIMIT
                    return config
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"配置文件加载失败: {e}")
                return self.create_default_config()
        else:
            logger.info("配置文件不存在，创建默认配置")
            return self.create_default_config()
            
    def create_default_config(self):
        """创建默认配置"""
        default_config = {"draw_limit": DEFAULT_DRAW_LIMIT}
        self.save_config(default_config)
        return default_config
        
    def save_config(self, config):
        """保存配置到文件"""
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"配置文件保存失败: {e}")
            
    def get_draw_limit(self):
        """获取每日抽取限制"""
        return self.config.get("draw_limit", DEFAULT_DRAW_LIMIT)
        
    def set_draw_limit(self, limit):
        """设置每日抽取限制"""
        if isinstance(limit, int) and limit > 0:
            self.config["draw_limit"] = limit
            self.save_config(self.config)
        else:
            logger.error(f"无效的抽取限制值: {limit}")

async def daily_reset(config_manager):
    """每日重置任务，在凌晨0点清空记录"""
    while True:
        now = datetime.datetime.now()
        # 计算到下一个凌晨0点的时间
        tomorrow = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        sleep_time = (tomorrow - now).total_seconds()
        
        logger.info(f"下次重置时间: {tomorrow}, 等待 {sleep_time:.0f} 秒")
        await asyncio.sleep(sleep_time)
        
        daily_records.clear()
        daily_counts.clear()
        logger.info("每日记录已重置")

@register("choulaopo", "糯米茨", "[仅napcat]这是用于抽取QQ群友当老婆的插件", "1.0.5")
class ChouLaoPo(Star):
    """抽老婆插件主类"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_manager = ConfigManager(CONFIG_PATH)
        # 启动每日重置任务
        asyncio.create_task(daily_reset(self.config_manager))

    def _build_message_chain(self, sender_id, user_id, nickname, avatar_url, at_selected_user):
        """构建消息链"""
        if at_selected_user:
            return [
                Comp.At(qq=sender_id),
                Comp.Plain(" 你的今日老婆是"),
                Comp.Image.fromURL(avatar_url),
                Comp.At(qq=user_id)
            ]
        else:
            return [
                Comp.At(qq=sender_id),
                Comp.Plain(" 你的今日老婆是"),
                Comp.Image.fromURL(avatar_url),
                Comp.Plain(nickname)
            ]

    async def _get_group_members(self, event: AstrMessageEvent):
        """获取群成员列表"""
        if event.get_platform_name() != "aiocqhttp":
            raise ValueError("此插件仅支持aiocqhttp平台")
            
        assert isinstance(event, AiocqhttpMessageEvent)
        client = event.bot
        group_id = event.get_group_id()
        
        payloads = {
            "group_id": group_id,
            "no_cache": True
        }
        
        try:
            ret = await client.api.call_action('get_group_member_list', **payloads)
            if not ret or len(ret) == 0:
                raise ValueError("无法获取群成员列表或群为空")
            return ret
        except Exception as e:
            logger.error(f"获取群成员列表失败: {e}")
            raise

    async def _draw_wife(self, event: AstrMessageEvent, at_selected_user: bool):
        """抽取老婆的核心逻辑"""
        try:
            # 获取发送者ID
            sender_id = event.get_sender_id()
            
            # 检查每日抽取限制
            draw_limit = self.config_manager.get_draw_limit()
            user_count = daily_counts.get(sender_id, 0)
            
            if user_count >= draw_limit:
                yield event.plain_result(f"今日抽取已达上限({draw_limit}次)")
                event.stop_event()
                return

            # 获取群成员列表
            members = await self._get_group_members(event)
            
            # 随机选择一个成员
            selected_member = random.choice(members)
            user_id = selected_member.get('user_id')
            nickname = selected_member.get('nickname', '未知用户')
            avatar_url = AVATAR_URL_TEMPLATE.format(user_id)

            # 构建消息链
            chain = self._build_message_chain(sender_id, user_id, nickname, avatar_url, at_selected_user)

            # 记录抽取结果
            daily_records[sender_id] = {
                "user_id": user_id,
                "nickname": nickname
            }
            daily_counts[sender_id] = user_count + 1
            
            yield event.chain_result(chain)
            
        except ValueError as e:
            logger.warning(f"抽取失败: {e}")
            yield event.plain_result(f"抽取失败: {e}")
            event.stop_event()
        except Exception as e:
            logger.error(f"抽取过程中发生未知错误: {e}")
            yield event.plain_result("抽取过程中发生错误，请稍后重试")
            event.stop_event()

    @filter.command("今日老婆", alias={'抽取', '抽老婆'})
    async def wife_with_at(self, event: AstrMessageEvent):
        """抽取今日老婆并@被选中的用户"""
        async for result in self._draw_wife(event, True):
            yield result

    @filter.command("今日老婆-@", alias={'抽取-@', '抽老婆-@'})
    async def wife_without_at(self, event: AstrMessageEvent):
        """抽取今日老婆但不@被选中的用户"""
        async for result in self._draw_wife(event, False):
            yield result

    @filter.command("今日记录", alias={'记录'})
    async def today_record(self, event: AstrMessageEvent):
        """查看今日抽取记录"""
        sender_id = event.get_sender_id()
        record = daily_records.get(sender_id)
        
        if record:
            chain = [
                Comp.At(qq=sender_id),
                Comp.Plain(" 你今日抽到的老婆是："),
                Comp.Plain(record["nickname"]),
                Comp.Plain(f" (QQ: {record['user_id']})")
            ]
            yield event.chain_result(chain)
        else:
            yield event.plain_result("你今日还未抽取老婆")

    @filter.command("老婆帮助", alias={'help'})
    async def help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """
            "帮助信息：\n"
            "/今日老婆 - 抽取今日老婆并@对方\n"
            "/今日老婆-@ - 抽取今日老婆但不@对方\n"
            "/今日记录 - 查看抽取记录\n"
            "/老婆帮助 - 查看当前插件帮助"
        """
        yield event.plain_result(help_text)
