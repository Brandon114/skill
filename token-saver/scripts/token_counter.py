#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 计数器 - 估算输入输出的 token 用量
"""

import sys
import os

def estimate_tokens(text):
    """
    估算文本的 token 数量
    
    中文：约 1.5-2 字符 = 1 token
    英文：约 4 字符 = 1 token
    代码：约 3-4 字符 = 1 token
    
    Args:
        text: 输入文本
        
    Returns:
        int: 预估的 token 数量
    """
    if not text:
        return 0
    
    # 检测文本类型
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    has_code = any(keyword in text for keyword in ['def ', 'class ', 'import ', 'function ', '{', '}', ';'])
    
    if has_chinese and has_code:
        # 混合内容
        return len(text) // 2
    elif has_chinese:
        # 主要是中文
        return int(len(text) / 1.5)
    elif has_code:
        # 代码
        return len(text) // 3
    else:
        # 英文
        return len(text) // 4

def count_conversation_tokens(messages):
    """
    计算整个对话的 token 用量
    
    Args:
        messages: 对话消息列表
        
    Returns:
        dict: {'input': X, 'output': Y, 'total': Z}
    """
    input_tokens = 0
    output_tokens = 0
    
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        tokens = estimate_tokens(content)
        
        if role == 'user':
            input_tokens += tokens
        else:
            output_tokens += tokens
    
    return {
        'input': input_tokens,
        'output': output_tokens,
        'total': input_tokens + output_tokens
    }

def estimate_cost(tokens, model='gpt-4'):
    """
    估算 API 成本（美元）
    
    Args:
        tokens: token 数量
        model: 模型名称
        
    Returns:
        float: 预估成本（美元）
    """
    # 价格 per 1K tokens (输入/输出)
    pricing = {
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-3.5': {'input': 0.0015, 'output': 0.002},
        'claude-3': {'input': 0.015, 'output': 0.075}
    }
    
    if model not in pricing:
        model = 'gpt-4'  # 默认
    
    prices = pricing[model]
    input_cost = (tokens * 0.5) * prices['input'] / 1000
    output_cost = (tokens * 0.5) * prices['output'] / 1000
    
    return input_cost + output_cost

if __name__ == '__main__':
    # 测试
    test_text = "这是一个测试文本，用于估算 token 数量。"
    tokens = estimate_tokens(test_text)
    print(f"文本: {test_text}")
    print(f"预估 tokens: {tokens}")
