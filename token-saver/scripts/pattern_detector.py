#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式检测器与脚本生成器 - 识别重复操作并生成可复用脚本
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    """重复模式类型"""
    EXACT_MATCH = "exact_match"           # 完全匹配
    SIMILAR_INTENT = "similar_intent"     # 相似意图
    SEQUENCE_MATCH = "sequence_match"     # 操作序列匹配

@dataclass
class DetectedPattern:
    """检测到的模式"""
    pattern_type: PatternType
    match_count: int
    examples: List[str]
    estimated_savings: int
    script_type: str  # 'bash', 'python', 'codebuddy_command'

class PatternDetector:
    """模式检测器类"""
    
    def __init__(self, threshold: int = 3, history_size: int = 20):
        """
        初始化模式检测器
        
        Args:
            threshold: 触发脚本生成的最小重复次数
            history_size: 保存的历史记录大小
        """
        self.threshold = threshold
        self.history_size = history_size
        self.recent_requests = []  # 最近的用户请求
        self.operation_sequences = []  # 操作序列指纹
        
    def analyze_request(self, user_input: str, tool_calls: List[Dict]) -> Optional[DetectedPattern]:
        """
        分析用户请求，检测重复模式
        
        Args:
            user_input: 用户输入
            tool_calls: 工具调用列表
            
        Returns:
            DetectedPattern or None: 如果检测到模式，返回模式信息
        """
        # 记录请求
        self.recent_requests.append({
            'input': user_input,
            'tools': tool_calls,
            'timestamp': len(self.recent_requests)
        })
        
        # 保持历史记录在限定大小内
        if len(self.recent_requests) > self.history_size:
            self.recent_requests = self.recent_requests[-self.history_size:]
        
        # 1. 检测完全相同的请求
        exact_matches = self._find_exact_matches(user_input)
        if exact_matches >= self.threshold:
            return DetectedPattern(
                pattern_type=PatternType.EXACT_MATCH,
                match_count=exact_matches,
                examples=self._get_recent_examples(user_input, exact=True),
                estimated_savings=exact_matches * 500,  # 预估每次节省 500 tokens
                script_type=self._determine_script_type(user_input)
            )
        
        # 2. 检测相似意图
        similar_matches = self._find_similar_intents(user_input)
        if similar_matches >= self.threshold:
            return DetectedPattern(
                pattern_type=PatternType.SIMILAR_INTENT,
                match_count=similar_matches,
                examples=self._get_recent_examples(user_input, exact=False),
                estimated_savings=similar_matches * 500,
                script_type='python'  # 相似意图通常用 Python 脚本处理
            )
        
        # 3. 检测重复的操作序列
        if tool_calls:
            sequence_hash = self._hash_operation_sequence(tool_calls)
            sequence_matches = self._find_sequence_matches(sequence_hash)
            if sequence_matches >= self.threshold:
                return DetectedPattern(
                    pattern_type=PatternType.SEQUENCE_MATCH,
                    match_count=sequence_matches,
                    examples=[f"操作序列（哈希: {sequence_hash[:8]}...）"],
                    estimated_savings=sequence_matches * 800,  # 操作序列节省更多
                    script_type='bash'
                )
        
        return None
    
    def _find_exact_matches(self, input_text: str) -> int:
        """查找完全相同的请求"""
        count = 0
        for req in self.recent_requests[:-1]:  # 不包含当前请求
            if req['input'] == input_text:
                count += 1
        return count
    
    def _find_similar_intents(self, input_text: str) -> int:
        """查找相似意图（使用简单的相似度检测）"""
        count = 0
        for req in self.recent_requests[:-1]:
            similarity = self._calculate_similarity(input_text, req['input'])
            if similarity > 0.8:  # 80% 以上相似度
                count += 1
        return count
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度（简单实现）
        
        Returns:
            float: 0-1 之间的相似度
        """
        # 移除空格后比较
        t1 = re.sub(r'\s+', '', text1)
        t2 = re.sub(r'\s+', '', text2)
        
        # 如果一方包含在另一方中
        if t1 in t2 or t2 in t1:
            return 0.9
        
        # 计算字符重合度
        set1 = set(t1)
        set2 = set(t2)
        
        if not set1 or not set2:
            return 0.0
        
        overlap = len(set1 & set2) / len(set1 | set2)
        return overlap
    
    def _hash_operation_sequence(self, tool_calls: List[Dict]) -> str:
        """生成操作序列的指纹（哈希）"""
        import hashlib
        
        # 将工具调用序列转换为字符串
        seq_str = '|'.join([
            f"{call.get('tool', '')}:{str(call.get('params', ''))}"
            for call in tool_calls
        ])
        
        # 生成哈希
        return hashlib.md5(seq_str.encode()).hexdigest()
    
    def _find_sequence_matches(self, sequence_hash: str) -> int:
        """查找重复的操作序列"""
        count = 0
        for seq_hash in self.operation_sequences[:-1]:  # 不包含当前序列
            if seq_hash == sequence_hash:
                count += 1
        return count
    
    def _get_recent_examples(self, input_text: str, exact: bool = True) -> List[str]:
        """获取最近的相似请求示例"""
        examples = []
        for req in self.recent_requests[-self.threshold:]:  # 最近 N 个
            if exact:
                if req['input'] == input_text:
                    examples.append(req['input'])
            else:
                similarity = self._calculate_similarity(input_text, req['input'])
                if similarity > 0.8:
                    examples.append(req['input'])
        return examples[:3]  # 最多返回 3 个示例
    
    def _determine_script_type(self, user_input: str) -> str:
        """判断应该生成哪种类型的脚本"""
        input_lower = user_input.lower()
        
        # Bash 脚本关键词
        bash_keywords = ['运行', '执行', '命令', 'run', 'execute', 'bash', 'shell']
        if any(kw in input_lower for kw in bash_keywords):
            return 'bash'
        
        # Python 脚本关键词
        python_keywords = ['分析', '处理', '计算', 'analyze', 'process', 'calculate']
        if any(kw in input_lower for kw in python_keywords):
            return 'python'
        
        # CodeBuddy 命令关键词
        cb_keywords = ['检查', '查询', '查看', 'check', 'query', 'view']
        if any(kw in input_lower for kw in cb_keywords):
            return 'codebuddy_command'
        
        # 默认
        return 'bash'

class ScriptGenerator:
    """脚本生成器类"""
    
    def __init__(self, template_dir: str = "templates"):
        """
        初始化脚本生成器
        
        Args:
            template_dir: 模板目录
        """
        self.template_dir = template_dir
        
    def generate_script(self, pattern: DetectedPattern) -> Tuple[str, str]:
        """
        根据检测到的模式生成脚本
        
        Args:
            pattern: 检测到的模式
            
        Returns:
            tuple: (脚本内容, 脚本文件名)
        """
        if pattern.script_type == 'bash':
            return self._generate_bash_script(pattern)
        elif pattern.script_type == 'python':
            return self._generate_python_script(pattern)
        elif pattern.script_type == 'codebuddy_command':
            return self._generate_codebuddy_command(pattern)
        else:
            return self._generate_bash_script(pattern)  # 默认生成 bash 脚本
    
    def _generate_bash_script(self, pattern: DetectedPattern) -> Tuple[str, str]:
        """生成 Bash 脚本"""
        script_lines = [
            "#!/bin/bash",
            "# 自动生成的脚本 - " + pattern.pattern_type.value,
            f"# 触发原因：检测到重复的操作模式 ({pattern.match_count} 次)",
            "",
            "# 请在下方添加您的命令",
            "echo '执行的任务：'",
        ]
        
        # 根据示例生成命令
        for i, example in enumerate(pattern.examples, 1):
            # 提取关键信息（简单实现）
            script_lines.append(f"echo '任务 {i}: {example[:50]}...'")
        
        script_lines.extend([
            "",
            "echo '✅ 脚本执行完成'",
        ])
        
        script_content = '\n'.join(script_lines)
        filename = f"auto_generated_script_{pattern.pattern_type.value}.sh"
        
        return script_content, filename
    
    def _generate_python_script(self, pattern: DetectedPattern) -> Tuple[str, str]:
        """生成 Python 脚本"""
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f"# 自动生成的脚本 - {pattern.pattern_type.value}",
            f"# 触发原因：检测到重复的操作模式 ({pattern.match_count} 次)",
            "",
            "import sys",
            "import argparse",
            "",
            "def main():",
            "    parser = argparse.ArgumentParser(description='自动生成的脚本')",
            "    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')",
            "    args = parser.parse_args()",
            "",
            "    print('执行的任务：')",
        ]
        
        # 根据示例生成任务
        for i, example in enumerate(pattern.examples, 1):
            script_lines.append(f"    print(f'任务 {i}: {example[:50]}...')")
        
        script_lines.extend([
            "",
            "    print('✅ 脚本执行完成')",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ])
        
        script_content = '\n'.join(script_lines)
        filename = f"auto_generated_script_{pattern.pattern_type.value}.py"
        
        return script_content, filename
    
    def _generate_codebuddy_command(self, pattern: DetectedPattern) -> Tuple[str, str]:
        """生成 CodeBuddy 命令"""
        command_lines = [
            "# CodeBuddy 命令 - " + pattern.pattern_type.value,
            f"# 触发原因：检测到重复的操作模式 ({pattern.match_count} 次)",
            "",
            "name: auto-generated-command",
            "description: 自动生成的命令",
            "pattern: ",
            "handler:",
            "  type: script",
            "  script: |",
        ]
        
        # 添加执行逻辑
        for example in pattern.examples:
            command_lines.append(f"    echo '执行: {example[:50]}...'")
        
        command_content = '\n'.join(command_lines)
        filename = f"auto_generated_command_{pattern.pattern_type.value}.yaml"
        
        return command_content, filename

if __name__ == '__main__':
    # 测试
    detector = PatternDetector(threshold=3)
    generator = ScriptGenerator()
    
    # 模拟重复请求
    test_inputs = [
        "检查 main.py 语法",
        "检查 utils.py 语法",
        "检查 config.py 语法",
    ]
    
    for text in test_inputs:
        result = detector.analyze_request(text, [])
        if result:
            print(f"\n✅ 检测到重复模式！")
            print(f"类型: {result.pattern_type.value}")
            print(f"重复次数: {result.match_count}")
            print(f"预估节省: {result.estimated_savings} tokens")
            
            # 生成脚本
            script_content, filename = generator.generate_script(result)
            print(f"\n生成的脚本: {filename}")
            print("=" * 50)
            print(script_content)
            break  # 只生成一次
