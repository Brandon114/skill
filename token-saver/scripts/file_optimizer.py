#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件读取优化器 - 避免重复和过度的文件读取
"""

import os
from typing import Dict, List, Optional, Tuple

class FileOptimizer:
    """文件读取优化器类"""
    
    def __init__(self, cache_expiry_rounds: int = 3, max_file_lines: int = 500):
        """
        初始化文件优化器
        
        Args:
            cache_expiry_rounds: 缓存过期轮次
            max_file_lines: 大文件阈值（行数）
        """
        self.cache = {}  # {file_path: {'content': ..., 'round': ...}}
        self.cache_expiry_rounds = cache_expiry_rounds
        self.max_file_lines = max_file_lines
        self.current_round = 0
        
    def should_use_cache(self, file_path: str, current_round: int) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该使用缓存
        
        Args:
            file_path: 文件路径
            current_round: 当前轮次
            
        Returns:
            tuple: (是否使用缓存, 缓存内容)
        """
        if file_path not in self.cache:
            return False, None
        
        cache_info = self.cache[file_path]
        rounds_since_cache = current_round - cache_info['round']
        
        # 如果缓存未过期，使用缓存
        if rounds_since_cache <= self.cache_expiry_rounds:
            return True, cache_info['content']
        
        # 缓存已过期，删除
        del self.cache[file_path]
        return False, None
    
    def update_cache(self, file_path: str, content: str, current_round: int):
        """
        更新文件缓存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            current_round: 当前轮次
        """
        self.cache[file_path] = {
            'content': content,
            'round': current_round
        }
        self.current_round = current_round
    
    def should_read_partial(self, file_path: str, target_line: Optional[int] = None) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        判断是否应该只读取文件片段
        
        Args:
            file_path: 文件路径
            target_line: 目标行号（如果知道）
            
        Returns:
            tuple: (是否读取片段, 起始行, 结束行)
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False, None, None
        
        # 检查文件行数
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                total_lines = sum(1 for _ in f)
        except:
            return False, None, None
        
        # 如果文件较小，读取整个文件
        if total_lines <= self.max_file_lines:
            return False, None, None
        
        # 如果文件较大且指定了目标行，读取该行人近区域
        if target_line is not None:
            start_line = max(1, target_line - 10)
            end_line = min(total_lines, target_line + 10)
            return True, start_line, end_line
        
        # 文件较大但未指定目标行，建议用户指定
        return True, 1, 50  # 默认读取前 50 行
    
    def should_batch_read(self, file_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        判断是否应该批量读取文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            tuple: (是否批量读取, 优化后的文件列表)
        """
        if len(file_paths) <= 1:
            return False, file_paths
        
        # 过滤掉二进制文件
        filtered_paths = []
        for path in file_paths:
            if self._is_binary_file(path):
                continue
            filtered_paths.append(path)
        
        return len(filtered_paths) > 1, filtered_paths
    
    def _is_binary_file(self, file_path: str) -> bool:
        """
        判断文件是否为二进制文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否是二进制文件
        """
        binary_extensions = ['.exe', '.dll', '.so', '.pyc', '.pdf', '.png', '.jpg', '.zip', '.tar', '.gz']
        _, ext = os.path.splitext(file_path.lower())
        return ext in binary_extensions
    
    def estimate_savings(self, file_path: str, use_cache: bool, read_partial: bool) -> Dict:
        """
        估算优化可以节省的 token 量
        
        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存
            read_partial: 是否读取片段
            
        Returns:
            dict: {'original': X, 'optimized': Y, 'saved': Z}
        """
        if not os.path.exists(file_path):
            return {'original': 0, 'optimized': 0, 'saved': 0}
        
        # 估算原始 token（读取整个文件）
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_tokens = len(content) // 4
        except:
            original_tokens = 1000  # 估算值
        
        # 估算优化后的 token
        optimized_tokens = original_tokens
        
        if use_cache:
            # 使用缓存，几乎不消耗 token
            optimized_tokens = 10
        elif read_partial:
            # 读取片段，约节省 70%
            optimized_tokens = int(original_tokens * 0.3)
        
        return {
            'original': original_tokens,
            'optimized': optimized_tokens,
            'saved': original_tokens - optimized_tokens
        }

if __name__ == '__main__':
    # 测试
    optimizer = FileOptimizer()
    
    # 模拟文件读取优化
    test_file = __file__  # 使用当前文件作为测试
    
    # 检查是否应该读取片段
    should_partial, start, end = optimizer.should_read_partial(test_file, target_line=10)
    print(f"是否读取片段: {should_partial}")
    if should_partial:
        print(f"建议读取行: {start} - {end}")
    
    # 估算节省量
    savings = optimizer.estimate_savings(test_file, use_cache=False, read_partial=should_partial)
    print(f"\n预估 Token 消耗:")
    print(f"  原始: {savings['original']}")
    print(f"  优化后: {savings['optimized']}")
    print(f"  节省: {savings['saved']}")
