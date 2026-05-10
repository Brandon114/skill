#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出控制器 - 根据用户任务类型自动调整输出详细程度
"""

from typing import Dict, List, Optional
from enum import Enum

class OutputMode(Enum):
    """输出模式枚举"""
    SHORT = "short"       # 简短模式
    NORMAL = "normal"     # 正常模式
    DETAIL = "detail"     # 详细模式
    DEBUG = "debug"       # 调试模式

class TaskType(Enum):
    """任务类型枚举"""
    CODE_DEBUG = "code_debug"         # 代码调试
    FILE_READ = "file_read"           # 文件读取
    CONCEPT_EXPLAIN = "concept"      # 概念解释
    CODE_GEN = "code_gen"            # 代码生成
    DATA_ANALYSIS = "data_analysis"   # 数据分析
    GENERAL = "general"              # 通用任务

class OutputController:
    """输出控制器类"""
    
    # 任务类型到默认输出模式的映射
    TASK_MODE_MAP = {
        TaskType.CODE_DEBUG: OutputMode.DETAIL,
        TaskType.FILE_READ: OutputMode.SHORT,
        TaskType.CONCEPT_EXPLAIN: OutputMode.NORMAL,
        TaskType.CODE_GEN: OutputMode.SHORT,
        TaskType.DATA_ANALYSIS: OutputMode.NORMAL,
        TaskType.GENERAL: OutputMode.NORMAL,
    }
    
    def __init__(self, default_mode: OutputMode = OutputMode.NORMAL):
        """
        初始化输出控制器
        
        Args:
            default_mode: 默认输出模式
        """
        self.current_mode = default_mode
        self.auto_mode = True  # 是否自动根据任务类型调整
        
    def detect_task_type(self, user_input: str, context: Optional[str] = None) -> TaskType:
        """
        检测用户任务类型
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可选）
            
        Returns:
            TaskType: 任务类型
        """
        input_lower = user_input.lower()
        
        # 代码调试关键词
        debug_keywords = ['bug', '错误', '报错', '异常', 'debug', '修复', 'fix']
        if any(kw in input_lower for kw in debug_keywords):
            return TaskType.CODE_DEBUG
        
        # 文件读取关键词
        read_keywords = ['读取', '查看', '打开文件', 'read', 'open', 'cat', '显示内容']
        if any(kw in input_lower for kw in read_keywords):
            return TaskType.FILE_READ
        
        # 概念解释关键词
        concept_keywords = ['什么是', '解释', '讲解', '介绍', 'what is', 'explain']
        if any(kw in input_lower for kw in concept_keywords):
            return TaskType.CONCEPT_EXPLAIN
        
        # 代码生成关键词
        gen_keywords = ['生成', '创建', '写', '实现', 'generate', 'create', 'write']
        if any(kw in input_lower for kw in gen_keywords):
            return TaskType.CODE_GEN
        
        # 数据分析关键词
        analysis_keywords = ['分析', '统计', '可视化', 'analyze', 'plot', 'chart']
        if any(kw in input_lower for kw in analysis_keywords):
            return TaskType.DATA_ANALYSIS
        
        return TaskType.GENERAL
    
    def get_output_mode(self, user_input: str, context: Optional[str] = None) -> OutputMode:
        """
        获取当前任务应该使用的输出模式
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可选）
            
        Returns:
            OutputMode: 输出模式
        """
        # 如果用户手动设置了模式，且关闭了自动模式，则使用手动设置
        if not self.auto_mode:
            return self.current_mode
        
        # 自动检测任务类型并选择模式
        task_type = self.detect_task_type(user_input, context)
        return self.TASK_MODE_MAP.get(task_type, OutputMode.NORMAL)
    
    def set_mode(self, mode: OutputMode):
        """
        手动设置输出模式
        
        Args:
            mode: 输出模式
        """
        self.current_mode = mode
        self.auto_mode = False
        
    def enable_auto_mode(self):
        """启用自动模式选择"""
        self.auto_mode = True
        
    def format_output(self, content: str, mode: Optional[OutputMode] = None) -> str:
        """
        根据输出模式格式化内容
        
        Args:
            content: 原始内容
            mode: 输出模式（如果为 None，使用当前模式）
            
        Returns:
            str: 格式化后的内容
        """
        if mode is None:
            mode = self.current_mode
        
        if mode == OutputMode.SHORT:
            # 简短模式：只保留核心信息
            return self._shorten(content)
        elif mode == OutputMode.NORMAL:
            # 正常模式：保留主要信息，去除冗余
            return self._normalize(content)
        elif mode == OutputMode.DETAIL:
            # 详细模式：保留所有信息
            return content
        elif mode == OutputMode.DEBUG:
            # 调试模式：添加调试信息
            return self._add_debug_info(content)
        
        return content
    
    def _shorten(self, content: str) -> str:
        """缩短内容（提取核心）"""
        # 简单实现：取前 500 字符 + 省略提示
        if len(content) > 500:
            return content[:500] + "\n\n... (内容已截断，使用 /token-saver mode detail 查看完整输出)"
        return content
    
    def _normalize(self, content: str) -> str:
        """正常化内容（去除冗余）"""
        # 简单实现：去除过多的空行和重复内容
        lines = content.split('\n')
        result = []
        prev_line = None
        
        for line in lines:
            # 跳过连续空行
            if line.strip() == '' and prev_line == '':
                continue
            result.append(line)
            prev_line = line.strip()
        
        return '\n'.join(result)
    
    def _add_debug_info(self, content: str) -> str:
        """添加调试信息"""
        debug_header = "[DEBUG MODE] 详细输出已启用\n"
        debug_footer = "\n[END OF DEBUG OUTPUT]"
        return debug_header + content + debug_footer
    
    def estimate_savings(self, content: str, from_mode: OutputMode, to_mode: OutputMode) -> Dict:
        """
        估算切换输出模式可以节省的 token 量
        
        Args:
            content: 内容文本
            from_mode: 原始模式
            to_mode: 目标模式
            
        Returns:
            dict: {'original_tokens': X, 'optimized_tokens': Y, 'saved': Z}
        """
        original_tokens = len(content) // 4  # 简单估算
        
        optimized_content = self.format_output(content, to_mode)
        optimized_tokens = len(optimized_content) // 4
        
        return {
            'original_tokens': original_tokens,
            'optimized_tokens': optimized_tokens,
            'saved': original_tokens - optimized_tokens
        }

if __name__ == '__main__':
    # 测试
    controller = OutputController()
    
    test_inputs = [
        "这个代码有 bug，帮我修复",
        "读取 config.json 文件",
        "解释一下什么是递归",
        "生成一个 Python 函数",
        "分析这些数据"
    ]
    
    for text in test_inputs:
        task_type = controller.detect_task_type(text)
        mode = controller.get_output_mode(text)
        print(f"\n输入: {text}")
        print(f"任务类型: {task_type.value}")
        print(f"推荐模式: {mode.value}")
