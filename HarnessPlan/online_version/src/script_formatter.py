"""
脚本格式转换模块

处理大括号格式与 HTML 删除线格式之间的双向转换。

大括号格式（后端存储）: 这是{要删除的内容}保留的内容
HTML 格式（前端展示）: 这是<del>要删除的内容</del>保留的内容
"""

import re
from typing import Dict, List


def script_to_delete_ranges(script: str) -> List[Dict[str, int]]:
    """
    从大括号格式脚本提取删除范围
    
    Args:
        script: 大括号格式，如 "这是{要删除的内容}保留的内容"
    
    Returns:
        删除范围列表，每个元素包含 start, end 索引（end 为排他性）
        [{"start": 2, "end": 10}, ...]
        
    Example:
        >>> script_to_delete_ranges("这是{要删除的内容}保留的内容")
        [{"start": 2, "end": 10}]
        
    Note:
        返回的范围索引基于**可见文本**（即不包含大括号本身），
        因此 "这是{删除}保留" 中 "删除" 的范围是 (2, 6)
    """
    ranges = []
    stack = []
    text_index = 0
    
    for char in script:
        if char == '{':
            stack.append(text_index)
        elif char == '}':
            if stack:
                start = stack.pop()
                if not stack:  # 只有最外层闭合时才记录
                    ranges.append({"start": start, "end": text_index})
        else:
            text_index += 1
    
    return ranges


def script_to_html(script: str) -> str:
    """
    将大括号格式脚本转换为 HTML 删除线格式
    
    Args:
        script: 大括号格式，如 "这是{要删除的内容}保留的内容"
    
    Returns:
        HTML 格式，如 "这是<del>要删除的内容</del>保留的内容"
        
    Example:
        >>> script_to_html("这是{要删除的内容}保留的内容")
        "这是<del>要删除的内容</del>保留的内容"
    """
    result = []
    current_deleted = []
    depth = 0
    
    for char in script:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                # 最外层结束，将删除内容包裹在 <del> 中
                result.append(f"<del>{''.join(current_deleted)}</del>")
                current_deleted = []
            elif depth < 0:
                # 括号不匹配，当作普通字符处理
                depth = 0
                result.append('}')
        else:
            if depth > 0:
                current_deleted.append(char)
            else:
                result.append(char)
    
    # 处理未闭合的大括号
    if depth > 0 and current_deleted:
        result.append(f"<del>{''.join(current_deleted)}</del>")
    
    return ''.join(result)


def html_to_script(html: str) -> str:
    """
    将 HTML 删除线格式转换为大括号格式
    
    Args:
        html: HTML 格式，如 "这是<del>要删除的内容</del>保留的内容"
    
    Returns:
        大括号格式，如 "这是{要删除的内容}保留的内容"
        
    Example:
        >>> html_to_script("这是<del>要删除的内容</del>保留的内容")
        "这是{要删除的内容}保留的内容"
    """
    # 处理 <del>...</del> 标签
    result = re.sub(r'<del>(.*?)</del>', r'{\1}', html, flags=re.DOTALL)
    # 处理其他可能的标签（如 <strike>, <s> 等）
    result = re.sub(r'<(?:strike|s)>(.*?)</(?:strike|s)>', r'{\1}', result, flags=re.DOTALL)
    return result


def apply_delete_ranges(text: str, ranges: List[Dict[str, int]]) -> str:
    """
    对纯文本应用删除范围，生成大括号格式
    
    Args:
        text: 纯文本
        ranges: 删除范围列表 [{"start": 2, "end": 10}, ...]
    
    Returns:
        大括号格式脚本
        
    Example:
        >>> apply_delete_ranges("这是要删除的内容保留的内容", [{"start": 2, "end": 8}])
        "这是{要删除的内容}保留的内容"
    """
    if not ranges:
        return text
    
    # 按 start 排序并合并重叠范围
    sorted_ranges = sorted(ranges, key=lambda r: r["start"])
    merged_ranges = []
    
    for range_item in sorted_ranges:
        start, end = range_item["start"], range_item["end"]
        
        # 验证范围有效性
        if start < 0 or end > len(text) or start >= end:
            continue
            
        if not merged_ranges:
            merged_ranges.append([start, end])
        else:
            last_start, last_end = merged_ranges[-1]
            if start <= last_end:
                # 重叠或相邻，合并
                merged_ranges[-1][1] = max(last_end, end)
            else:
                merged_ranges.append([start, end])
    
    # 从后往前插入大括号，避免索引偏移问题
    result = list(text)
    for start, end in reversed(merged_ranges):
        result.insert(end, '}')
        result.insert(start, '{')
    
    return ''.join(result)


def validate_script_format(script: str) -> bool:
    """
    验证大括号格式是否合法（括号匹配）
    
    Args:
        script: 大括号格式脚本
    
    Returns:
        是否合法
        
    Example:
        >>> validate_script_format("这是{要删除的内容}保留的内容")
        True
        >>> validate_script_format("这是{要删除的内容保留的内容")
        False
        >>> validate_script_format("这是}}要删除的内容{{保留的内容")
        False
    """
    depth = 0
    
    for char in script:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth < 0:
                # 右括号多于左括号
                return False
    
    # 完全匹配时 depth 应该为 0
    return depth == 0


def extract_visible_text(script: str) -> str:
    """
    从大括号格式脚本中提取可见文本（去除所有删除内容）
    
    Args:
        script: 大括号格式脚本
    
    Returns:
        可见文本
        
    Example:
        >>> extract_visible_text("这是{要删除的内容}保留的内容")
        "这是保留的内容"
    """
    result = []
    depth = 0
    
    for char in script:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        else:
            if depth == 0:
                result.append(char)
    
    return ''.join(result)


def get_delete_ranges_diff(old_ranges: List[Dict[str, int]], 
                           new_ranges: List[Dict[str, int]]) -> Dict[str, List[Dict[str, int]]]:
    """
    比较两组删除范围的差异
    
    Args:
        old_ranges: 原始删除范围列表
        new_ranges: 新删除范围列表
    
    Returns:
        包含 added 和 removed 的字典
        
    Example:
        >>> old = [{"start": 2, "end": 5}]
        >>> new = [{"start": 2, "end": 5}, {"start": 8, "end": 10}]
        >>> get_delete_ranges_diff(old, new)
        {"added": [{"start": 8, "end": 10}], "removed": []}
    """
    old_set = {(r["start"], r["end"]) for r in old_ranges}
    new_set = {(r["start"], r["end"]) for r in new_ranges}
    
    added = [{"start": s, "end": e} for s, e in (new_set - old_set)]
    removed = [{"start": s, "end": e} for s, e in (old_set - new_set)]
    
    return {"added": added, "removed": removed}


if __name__ == "__main__":
    # 简单的自测
    print("=== 基本功能测试 ===")
    
    # 测试 script_to_delete_ranges
    script1 = "这是{要删除的内容}保留的内容"
    ranges1 = script_to_delete_ranges(script1)
    print(f"script_to_delete_ranges('{script1}') = {ranges1}")
    assert ranges1 == [{"start": 2, "end": 8}]
    
    # 测试 script_to_html
    html1 = script_to_html(script1)
    print(f"script_to_html('{script1}') = '{html1}'")
    assert html1 == "这是<del>要删除的内容</del>保留的内容"
    
    # 测试 html_to_script
    script2 = html_to_script(html1)
    print(f"html_to_script('{html1}') = '{script2}'")
    assert script2 == script1
    
    # 测试 apply_delete_ranges
    text = "这是要删除的内容保留的内容"
    script3 = apply_delete_ranges(text, [{"start": 2, "end": 8}])
    print(f"apply_delete_ranges('{text}', ...) = '{script3}'")
    assert script3 == "这是{要删除的内容}保留的内容"
    
    # 测试 validate_script_format
    print(f"validate_script_format('{script1}') = {validate_script_format(script1)}")
    assert validate_script_format(script1) == True
    print(f"validate_script_format('这是{{未闭合') = {validate_script_format('这是{未闭合')}")
    assert validate_script_format("这是{未闭合") == False
    
    print("\n=== 所有测试通过 ===")
