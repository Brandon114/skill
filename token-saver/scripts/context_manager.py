#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理器 - 主动管理对话历史，避免无意义的 token 累积
"""

from typing import Dict, List, Optional

class ContextManager:
    """上下文管理器类"""
    
    def __init__(self, threshold_rounds: int = 20, threshold_tokens: int = 8000):
        """
        初始化上下文管理器
        
        Args:
            threshold_rounds: 触发提醒的对话轮次阈值
            threshold_tokens: 触发提醒的 token 阈值
        """
        self.threshold_rounds = threshold_rounds
        self.threshold_tokens = threshold_tokens
        self.conversation_history = []
        
    def check_context(self, messages: List[Dict]) -> Dict:
        """
        检查上下文状态，判断是否需要提醒用户
        
        Args:
            messages: 对话消息列表
            
        Returns:
            dict: {
                'should_warn': 是否需要提醒,
                'rounds': 当前轮次,
                'estimated_tokens': 预估总 tokens,
                'suggestions': 建议操作列表
            }
        """
        # 计算对话轮次（每 2 条消息 = 1 轮）
        rounds = len(messages) // 2
        
        # 估算 token 用量
        estimated_tokens = self._estimate_tokens(messages)
        
        # 判断是否需要提醒
        should_warn = (rounds >= self.threshold_rounds or 
                      estimated_tokens >= self.threshold_tokens)
        
        # 生成建议
        suggestions = []
        if should_warn:
            suggestions = [
                "使用 /compact 压缩历史记录",
                "将关键信息保存到 memory",
                "开启新对话处理新任务"
            ]
        
        return {
            'should_warn': should_warn,
            'rounds': rounds,
            'estimated_tokens': estimated_tokens,
            'suggestions': suggestions
        }
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算消息列表的总 token 用量"""
        total = 0
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role', 'user')
            
            # 简单估算：中文 1.5 字符/token，英文 4 字符/token
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
            if has_chinese:
                tokens = int(len(content) / 1.5)
            else:
                tokens = len(content) // 4
            
            total += tokens
        
        return total
    
    def summarize_recent(self, messages: List[Dict], num_rounds: int = 5) -> str:
        """
        总结最近 N 轮对话的关键信息
        
        Args:
            messages: 对话消息列表
            num_rounds: 要总结的轮次数
            
        Returns:
            str: 总结文本
        """
        # 获取最近 2*num_rounds 条消息
        recent_messages = messages[-(num_rounds * 2):]
        
        summary_parts = []
        for i, msg in enumerate(recent_messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:100]  # 只取前 100 字符
            
            summary_parts.append(f"{role}: {content}...")
        
        return "\n".join(summary_parts)
    
    def extract_important_info(self, messages: List[Dict]) -> List[str]:
        """
        提取对话中的重要信息（可保存到 memory）
        
        Args:
            messages: 对话消息列表
            
        Returns:
            list: 重要信息列表
        """
        important_keywords = [
            '项目路径', '文件位置', '配置', '错误', 'bug',
            '决定', '选择', '确认', '记住', '注意'
        ]
        
        important_info = []
        for msg in messages:
            content = msg.get('content', '')
            
            # 检查是否包含重要关键词
            if any(keyword in content for keyword in important_keywords):
                # 提取关键句子（简单实现：取前 200 字符）
                info = content[:200].strip()
                if info and info not in important_info:
                    important_info.append(info)
        
        return important_info

if __name__ == '__main__':
    # 测试
    manager = ContextManager(threshold_rounds=5, threshold_tokens=1000)
    
    # 模拟对话历史
    test_messages = [
        {'role': 'user', 'content': '你好，帮我分析一下代码'},
        {'role': 'assistant', 'content': '好的，我来帮您分析'},
        {'role': 'user', 'content': '这个函数的逻辑有问题'},
        {'role': 'assistant', 'content': '我看到了，问题在第 10 行'},
        {'role': 'user', 'content': '能帮我修复吗？'},
        {'role': 'assistant', 'content': '当然，我来修复'},
    ]
    
    result = manager.check_context(test_messages)
    print(f"对话轮次: {result['rounds']}")
    print(f"预估 tokens: {result['estimated_tokens']}")
    print(f"需要提醒: {result['should_warn']}")
    if result['should_warn']:
        print("建议操作:")
        for suggestion in result['suggestions']:
            print(f"  - {suggestion}")
