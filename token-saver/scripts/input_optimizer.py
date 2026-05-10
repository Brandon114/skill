#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入优化器 - 检测并简化冗长的用户输入
"""

import re
from typing import Tuple, Dict

class InputOptimizer:
    """输入优化器类"""
    
    # 常见的冗余表达模式
    REDUNDANT_PATTERNS = [
        (r'请帮我(详细)?地?', ''),
        (r'能不能?', ''),
        (r'我想要?', ''),
        (r'我需要?', ''),
        (r'可以(帮我)?', ''),
        (r'一步一步(地)?', ''),
        (r'详细地?', ''),
        (r'仔细地?', ''),
        (r'认真地?', ''),
        (r'帮我?检查(一下)?', '检查'),
        (r'帮我?分析(一下)?', '分析'),
        (r'帮我?看看', '查看'),
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.REDUNDANT_PATTERNS
        ]
    
    def optimize(self, text: str) -> Dict:
        """
        优化用户输入
        
        Args:
            text: 原始输入文本
            
        Returns:
            dict: {
                'original': 原始文本,
                'optimized': 优化后文本,
                'original_tokens': 原始预估 tokens,
                'optimized_tokens': 优化后预估 tokens,
                'saved_tokens': 节省的 tokens,
                'saved_percent': 节省百分比
            }
        """
        # 估算原始 token
        original_tokens = self._estimate_tokens(text)
        
        # 应用优化规则
        optimized = text
        for pattern, replacement in self.compiled_patterns:
            optimized = pattern.sub(replacement, optimized)
        
        # 清理多余空格
        optimized = re.sub(r'\s+', ' ', optimized).strip()
        
        # 估算优化后 token
        optimized_tokens = self._estimate_tokens(optimized)
        
        # 计算节省量
        saved_tokens = original_tokens - optimized_tokens
        saved_percent = (saved_tokens / original_tokens * 100) if original_tokens > 0 else 0
        
        return {
            'original': text,
            'optimized': optimized,
            'original_tokens': original_tokens,
            'optimized_tokens': optimized_tokens,
            'saved_tokens': saved_tokens,
            'saved_percent': saved_percent
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量"""
        if not text:
            return 0
        
        # 简单估算：中文 1.5 字符/token，英文 4 字符/token
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        
        if has_chinese:
            return int(len(text) / 1.5)
        else:
            return len(text) // 4
    
    def detect_repetition(self, current_input: str, history: list) -> Tuple[bool, int]:
        """
        检测是否与历史输入重复
        
        Args:
            current_input: 当前输入
            history: 历史输入列表
            
        Returns:
            tuple: (是否重复, 重复次数)
        """
        if not history:
            return False, 0
        
        repeat_count = 0
        for hist_input in history[-5:]:  # 只检查最近 5 条
            if self._is_similar(current_input, hist_input):
                repeat_count += 1
        
        return repeat_count > 0, repeat_count
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """判断两段文本是否相似（简单实现）"""
        # 移除空格后比较
        t1 = re.sub(r'\s+', '', text1)
        t2 = re.sub(r'\s+', '', text2)
        
        # 如果长度差异 > 20%，认为不相似
        len_diff = abs(len(t1) - len(t2)) / max(len(t1), len(t2))
        if len_diff > 0.2:
            return False
        
        # 简单包含检查
        if t1 in t2 or t2 in t1:
            return True
        
        # 计算相似度（简单的字符重合度）
        set1 = set(t1)
        set2 = set(t2)
        overlap = len(set1 & set2) / len(set1 | set2)
        
        return overlap > 0.8  # 80% 以上重合度认为相似

if __name__ == '__main__':
    # 测试
    optimizer = InputOptimizer()
    
    test_inputs = [
        "请帮我详细地分析一下这个代码的每一个部分",
        "能不能帮我检查一下这个文件有没有错误",
        "我想要一步一步地了解这个功能是怎的工作的"
    ]
    
    for text in test_inputs:
        result = optimizer.optimize(text)
        print(f"\n原始: {result['original']}")
        print(f"优化: {result['optimized']}")
        print(f"节省: {result['saved_tokens']} tokens ({result['saved_percent']:.1f}%)")
