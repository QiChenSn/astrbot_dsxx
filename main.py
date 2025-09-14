import asyncio
import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("timed_message", "AstrBot开发者", "定时发送群聊消息插件", "1.0.0")
class TimedMessagePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_file = os.path.join(os.path.dirname(__file__), "timed_messages.json")
        self.tasks: Dict[str, asyncio.Task] = {}
        self.scheduled_messages: List[Dict] = []
        
    async def initialize(self):
        """插件初始化，加载配置并启动定时任务"""
        await self.load_config()
        await self.start_all_tasks()
        logger.info("定时消息插件初始化完成")
    
    async def load_config(self):
        """加载定时消息配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.scheduled_messages = json.load(f)
                logger.info(f"已加载 {len(self.scheduled_messages)} 条定时消息配置")
            else:
                self.scheduled_messages = []
                await self.save_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.scheduled_messages = []
    
    async def save_config(self):
        """保存定时消息配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.scheduled_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    async def start_all_tasks(self):
        """启动所有定时任务"""
        for msg_config in self.scheduled_messages:
            if msg_config.get('enabled', True):
                await self.start_single_task(msg_config)
    
    async def start_single_task(self, msg_config: Dict):
        """启动单个定时任务"""
        task_id = msg_config['id']
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
        
        self.tasks[task_id] = asyncio.create_task(self.timed_message_loop(msg_config))
        logger.info(f"已启动定时任务: {task_id}")
    
    async def timed_message_loop(self, msg_config: Dict):
        """定时消息循环"""
        try:
            while True:
                now = datetime.now()
                target_time = time.fromisoformat(msg_config['time'])
                current_time = now.time()
                
                # 计算下次执行时间
                next_run = datetime.combine(now.date(), target_time)
                if current_time >= target_time:
                    next_run = datetime.combine((now + timedelta(days=1)).date(), target_time)
                
                # 等待到执行时间
                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"任务 {msg_config['id']} 将在 {wait_seconds:.0f} 秒后执行")
                await asyncio.sleep(wait_seconds)
                
                # 发送消息
                await self.send_timed_message(msg_config)
                
        except asyncio.CancelledError:
            logger.info(f"定时任务 {msg_config['id']} 已取消")
        except Exception as e:
            logger.error(f"定时任务 {msg_config['id']} 执行出错: {e}")
    
    async def send_timed_message(self, msg_config: Dict):
        """发送定时消息"""
        try:
            group_id = msg_config['group_id']
            message = msg_config['message']
            
            # 使用AstrBot的消息发送API
            # 这里使用简化的方式，实际使用时需要根据AstrBot的具体API调整
            logger.info(f"发送定时消息到群 {group_id}: {message}")
            # 注意：这里需要根据实际的AstrBot API来实现消息发送
            # 由于不确定具体的API，这里只记录日志
                
        except Exception as e:
            logger.error(f"发送定时消息失败: {e}")
    
    @filter.command("add_timed_msg")
    async def add_timed_message(self, event: AstrMessageEvent):
        """添加定时消息
        用法: /add_timed_msg <群号> <时间(HH:MM)> <消息内容>
        示例: /add_timed_msg 123456789 09:00 早上好，新的一天开始了！
        """
        try:
            args = event.message_str.split(' ', 3)
            if len(args) < 4:
                yield event.plain_result("用法: /add_timed_msg <群号> <时间(HH:MM)> <消息内容>")
                return
            
            group_id = args[1]
            time_str = args[2]
            message = args[3]
            
            # 验证时间格式
            try:
                time.fromisoformat(time_str)
            except ValueError:
                yield event.plain_result("时间格式错误，请使用 HH:MM 格式，如 09:00")
                return
            
            # 创建新的定时消息配置
            msg_id = f"msg_{len(self.scheduled_messages) + 1}_{int(datetime.now().timestamp())}"
            new_config = {
                "id": msg_id,
                "group_id": group_id,
                "time": time_str,
                "message": message,
                "enabled": True,
                "created_at": datetime.now().isoformat()
            }
            
            self.scheduled_messages.append(new_config)
            await self.save_config()
            await self.start_single_task(new_config)
            
            yield event.plain_result(f"定时消息添加成功！\nID: {msg_id}\n群号: {group_id}\n时间: {time_str}\n消息: {message}")
            
        except Exception as e:
            logger.error(f"添加定时消息失败: {e}")
            yield event.plain_result(f"添加失败: {str(e)}")
    
    @filter.command("list_timed_msg")
    async def list_timed_messages(self, event: AstrMessageEvent):
        """列出所有定时消息"""
        if not self.scheduled_messages:
            yield event.plain_result("当前没有配置任何定时消息")
            return
        
        result = "当前配置的定时消息:\n"
        for i, msg in enumerate(self.scheduled_messages, 1):
            status = "启用" if msg.get('enabled', True) else "禁用"
            result += f"{i}. ID: {msg['id']}\n"
            result += f"   群号: {msg['group_id']}\n"
            result += f"   时间: {msg['time']}\n"
            result += f"   消息: {msg['message'][:50]}{'...' if len(msg['message']) > 50 else ''}\n"
            result += f"   状态: {status}\n\n"
        
        yield event.plain_result(result)
    
    @filter.command("del_timed_msg")
    async def delete_timed_message(self, event: AstrMessageEvent):
        """删除定时消息
        用法: /del_timed_msg <消息ID>
        """
        try:
            args = event.message_str.split(' ', 1)
            if len(args) < 2:
                yield event.plain_result("用法: /del_timed_msg <消息ID>")
                return
            
            msg_id = args[1]
            
            # 查找并删除消息
            found = False
            for i, msg in enumerate(self.scheduled_messages):
                if msg['id'] == msg_id:
                    # 取消任务
                    if msg_id in self.tasks:
                        self.tasks[msg_id].cancel()
                        del self.tasks[msg_id]
                    
                    # 从配置中删除
                    del self.scheduled_messages[i]
                    await self.save_config()
                    found = True
                    break
            
            if found:
                yield event.plain_result(f"定时消息 {msg_id} 已删除")
            else:
                yield event.plain_result(f"未找到ID为 {msg_id} 的定时消息")
                
        except Exception as e:
            logger.error(f"删除定时消息失败: {e}")
            yield event.plain_result(f"删除失败: {str(e)}")
    
    @filter.command("toggle_timed_msg")
    async def toggle_timed_message(self, event: AstrMessageEvent):
        """启用/禁用定时消息
        用法: /toggle_timed_msg <消息ID>
        """
        try:
            args = event.message_str.split(' ', 1)
            if len(args) < 2:
                yield event.plain_result("用法: /toggle_timed_msg <消息ID>")
                return
            
            msg_id = args[1]
            
            # 查找并切换状态
            found = False
            for msg in self.scheduled_messages:
                if msg['id'] == msg_id:
                    msg['enabled'] = not msg.get('enabled', True)
                    await self.save_config()
                    
                    if msg['enabled']:
                        await self.start_single_task(msg)
                        yield event.plain_result(f"定时消息 {msg_id} 已启用")
                    else:
                        if msg_id in self.tasks:
                            self.tasks[msg_id].cancel()
                            del self.tasks[msg_id]
                        yield event.plain_result(f"定时消息 {msg_id} 已禁用")
                    found = True
                    break
            
            if not found:
                yield event.plain_result(f"未找到ID为 {msg_id} 的定时消息")
                
        except Exception as e:
            logger.error(f"切换定时消息状态失败: {e}")
            yield event.plain_result(f"操作失败: {str(e)}")
    
    async def terminate(self):
        """插件终止时取消所有任务"""
        for task in self.tasks.values():
            task.cancel()
        logger.info("定时消息插件已终止，所有任务已取消")
