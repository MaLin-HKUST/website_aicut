"""
脚本格式转换模块的单元测试
"""

import pytest
from src.script_formatter import (
    script_to_delete_ranges,
    script_to_html,
    html_to_script,
    apply_delete_ranges,
    validate_script_format,
    extract_visible_text,
    get_delete_ranges_diff,
)


class TestScriptToDeleteRanges:
    """测试 script_to_delete_ranges 函数"""
    
    def test_single_delete_range(self):
        """测试单个删除范围"""
        script = "这是{要删除的内容}保留的内容"
        result = script_to_delete_ranges(script)
        # "要删除的内容" 是 6 个字符，start=2, end=2+6=8
        assert result == [{"start": 2, "end": 8}]
    
    def test_multiple_delete_ranges(self):
        """测试多个删除范围"""
        script = "{删除1}保留1{删除2}保留2"
        result = script_to_delete_ranges(script)
        assert result == [
            {"start": 0, "end": 3},
            {"start": 6, "end": 9}
        ]
    
    def test_no_delete_range(self):
        """测试无删除范围"""
        script = "这是没有删除内容的文本"
        result = script_to_delete_ranges(script)
        assert result == []
    
    def test_empty_string(self):
        """测试空字符串"""
        result = script_to_delete_ranges("")
        assert result == []
    
    def test_nested_braces(self):
        """测试嵌套大括号"""
        script = "这是{{嵌套内容}}保留"
        result = script_to_delete_ranges(script)
        # 嵌套时，只计算最外层的内容："{嵌套内容}" -> "嵌套内容" (4个字符)
        assert result == [{"start": 2, "end": 6}]
    
    def test_consecutive_delete_ranges(self):
        """测试连续的删除范围"""
        script = "这是{删1}{删2}保留"
        result = script_to_delete_ranges(script)
        assert result == [
            {"start": 2, "end": 4},
            {"start": 4, "end": 6}
        ]
    
    def test_braces_at_boundaries(self):
        """测试边界处的大括号"""
        script = "{开头删除}中间{结尾删除}"
        result = script_to_delete_ranges(script)
        assert result == [
            {"start": 0, "end": 4},
            {"start": 6, "end": 10}
        ]


class TestScriptToHtml:
    """测试 script_to_html 函数"""
    
    def test_single_delete(self):
        """测试单个删除转换"""
        script = "这是{要删除的内容}保留的内容"
        result = script_to_html(script)
        assert result == "这是<del>要删除的内容</del>保留的内容"
    
    def test_multiple_deletes(self):
        """测试多个删除转换"""
        script = "{删除1}保留1{删除2}保留2"
        result = script_to_html(script)
        assert result == "<del>删除1</del>保留1<del>删除2</del>保留2"
    
    def test_no_delete(self):
        """测试无删除内容"""
        script = "这是没有删除内容的文本"
        result = script_to_html(script)
        assert result == "这是没有删除内容的文本"
    
    def test_empty_string(self):
        """测试空字符串"""
        result = script_to_html("")
        assert result == ""
    
    def test_only_delete_content(self):
        """测试全部是删除内容"""
        script = "{全部删除}"
        result = script_to_html(script)
        assert result == "<del>全部删除</del>"
    
    def test_unmatched_opening_brace(self):
        """测试未闭合的左大括号"""
        script = "这是{未闭合"
        result = script_to_html(script)
        # 未闭合的内容也视为删除
        assert result == "这是<del>未闭合</del>"
    
    def test_unmatched_closing_brace(self):
        """测试多余的右大括号"""
        script = "这是}多余"
        result = script_to_html(script)
        assert result == "这是}多余"
    
    def test_nested_braces(self):
        """测试嵌套大括号"""
        script = "这是{{嵌套}}保留"
        result = script_to_html(script)
        # 嵌套时，内层的大括号不保留，只保留内容
        assert result == "这是<del>嵌套</del>保留"
    
    def test_empty_delete_content(self):
        """测试空的删除内容"""
        script = "这是{}保留"
        result = script_to_html(script)
        assert result == "这是<del></del>保留"


class TestHtmlToScript:
    """测试 html_to_script 函数"""
    
    def test_single_del_tag(self):
        """测试单个 <del> 标签"""
        html = "这是<del>要删除的内容</del>保留的内容"
        result = html_to_script(html)
        assert result == "这是{要删除的内容}保留的内容"
    
    def test_multiple_del_tags(self):
        """测试多个 <del> 标签"""
        html = "<del>删除1</del>保留1<del>删除2</del>保留2"
        result = html_to_script(html)
        assert result == "{删除1}保留1{删除2}保留2"
    
    def test_no_del_tag(self):
        """测试无 <del> 标签"""
        html = "这是没有删除内容的文本"
        result = html_to_script(html)
        assert result == "这是没有删除内容的文本"
    
    def test_empty_string(self):
        """测试空字符串"""
        result = html_to_script("")
        assert result == ""
    
    def test_strike_tag(self):
        """测试 <strike> 标签"""
        html = "这是<strike>删除内容</strike>保留"
        result = html_to_script(html)
        assert result == "这是{删除内容}保留"
    
    def test_s_tag(self):
        """测试 <s> 标签"""
        html = "这是<s>删除内容</s>保留"
        result = html_to_script(html)
        assert result == "这是{删除内容}保留"
    
    def test_multiline_content(self):
        """测试多行内容"""
        html = "这是<del>删除\n内容</del>保留"
        result = html_to_script(html)
        assert result == "这是{删除\n内容}保留"


class TestApplyDeleteRanges:
    """测试 apply_delete_ranges 函数"""
    
    def test_single_range(self):
        """测试单个删除范围"""
        text = "这是要删除的内容保留的内容"
        # "要删除的内容" 是 6 个字符，所以 end = 2 + 6 = 8
        ranges = [{"start": 2, "end": 8}]
        result = apply_delete_ranges(text, ranges)
        assert result == "这是{要删除的内容}保留的内容"
    
    def test_multiple_ranges(self):
        """测试多个删除范围"""
        text = "删除1保留1删除2保留2"
        ranges = [
            {"start": 0, "end": 3},
            {"start": 6, "end": 9}
        ]
        result = apply_delete_ranges(text, ranges)
        assert result == "{删除1}保留1{删除2}保留2"
    
    def test_empty_ranges(self):
        """测试空范围列表"""
        text = "这是没有删除的文本"
        result = apply_delete_ranges(text, [])
        assert result == "这是没有删除的文本"
    
    def test_overlapping_ranges(self):
        """测试重叠的删除范围（应合并）"""
        text = "这是一段要删除的内容"
        ranges = [
            {"start": 2, "end": 6},
            {"start": 5, "end": 10}
        ]
        result = apply_delete_ranges(text, ranges)
        # 重叠范围合并为 [2, 10]
        assert result == "这是{一段要删除的内容}"
    
    def test_adjacent_ranges(self):
        """测试相邻的删除范围（应合并）"""
        text = "删除A删除B保留"
        ranges = [
            {"start": 0, "end": 3},
            {"start": 3, "end": 6}
        ]
        result = apply_delete_ranges(text, ranges)
        # 相邻范围合并
        assert result == "{删除A删除B}保留"
    
    def test_invalid_range_negative_start(self):
        """测试无效范围：负数起始"""
        text = "这是文本"
        ranges = [{"start": -1, "end": 3}]
        result = apply_delete_ranges(text, ranges)
        # 无效范围被忽略
        assert result == "这是文本"
    
    def test_invalid_range_end_exceeds_length(self):
        """测试无效范围：结束超出长度"""
        text = "这是文本"
        ranges = [{"start": 2, "end": 100}]
        result = apply_delete_ranges(text, ranges)
        # 无效范围被忽略
        assert result == "这是文本"
    
    def test_invalid_range_start_greater_than_end(self):
        """测试无效范围：起始大于结束"""
        text = "这是文本"
        ranges = [{"start": 5, "end": 2}]
        result = apply_delete_ranges(text, ranges)
        # 无效范围被忽略
        assert result == "这是文本"


class TestValidateScriptFormat:
    """测试 validate_script_format 函数"""
    
    def test_valid_balanced_braces(self):
        """测试有效：平衡的大括号"""
        assert validate_script_format("这是{删除}保留") == True
        assert validate_script_format("{删除1}保留{删除2}") == True
    
    def test_valid_empty_script(self):
        """测试有效：空字符串"""
        assert validate_script_format("") == True
    
    def test_valid_no_braces(self):
        """测试有效：无大括号"""
        assert validate_script_format("这是纯文本") == True
    
    def test_invalid_unmatched_opening(self):
        """测试无效：未闭合的左大括号"""
        assert validate_script_format("这是{未闭合") == False
    
    def test_invalid_unmatched_closing(self):
        """测试无效：多余的右大括号"""
        assert validate_script_format("这是}多余") == False
    
    def test_invalid_more_closing(self):
        """测试无效：右括号多于左括号"""
        assert validate_script_format("这是}}双右括号{{") == False
    
    def test_invalid_nested_unbalanced(self):
        """测试无效：嵌套不平衡"""
        assert validate_script_format("这是{{未闭合") == False


class TestExtractVisibleText:
    """测试 extract_visible_text 函数"""
    
    def test_extract_visible(self):
        """测试提取可见文本"""
        script = "这是{要删除的内容}保留的内容"
        result = extract_visible_text(script)
        assert result == "这是保留的内容"
    
    def test_all_deleted(self):
        """测试全部删除的情况"""
        script = "{全部删除}"
        result = extract_visible_text(script)
        assert result == ""
    
    def test_no_deletion(self):
        """测试无删除的情况"""
        script = "全部保留"
        result = extract_visible_text(script)
        assert result == "全部保留"
    
    def test_empty_string(self):
        """测试空字符串"""
        result = extract_visible_text("")
        assert result == ""
    
    def test_nested_braces(self):
        """测试嵌套大括号"""
        script = "这是{{嵌套}}保留"
        result = extract_visible_text(script)
        assert result == "这是保留"


class TestGetDeleteRangesDiff:
    """测试 get_delete_ranges_diff 函数"""
    
    def test_no_diff(self):
        """测试无差异"""
        old = [{"start": 2, "end": 5}]
        new = [{"start": 2, "end": 5}]
        result = get_delete_ranges_diff(old, new)
        assert result == {"added": [], "removed": []}
    
    def test_added_range(self):
        """测试新增范围"""
        old = [{"start": 2, "end": 5}]
        new = [{"start": 2, "end": 5}, {"start": 8, "end": 10}]
        result = get_delete_ranges_diff(old, new)
        assert result == {"added": [{"start": 8, "end": 10}], "removed": []}
    
    def test_removed_range(self):
        """测试删除范围"""
        old = [{"start": 2, "end": 5}, {"start": 8, "end": 10}]
        new = [{"start": 2, "end": 5}]
        result = get_delete_ranges_diff(old, new)
        assert result == {"added": [], "removed": [{"start": 8, "end": 10}]}
    
    def test_added_and_removed(self):
        """测试既有新增又有删除"""
        old = [{"start": 2, "end": 5}]
        new = [{"start": 8, "end": 10}]
        result = get_delete_ranges_diff(old, new)
        assert result == {
            "added": [{"start": 8, "end": 10}],
            "removed": [{"start": 2, "end": 5}]
        }
    
    def test_empty_ranges(self):
        """测试空范围"""
        result = get_delete_ranges_diff([], [])
        assert result == {"added": [], "removed": []}


class TestRoundTrip:
    """测试往返转换"""
    
    def test_script_to_html_to_script(self):
        """测试 script -> html -> script 往返"""
        original = "这是{删除1}保留{删除2}"
        html = script_to_html(original)
        back = html_to_script(html)
        assert back == original
    
    def test_ranges_roundtrip(self):
        """测试范围往返"""
        original = "这是{删除1}保留{删除2}"
        ranges = script_to_delete_ranges(original)
        text = extract_visible_text(original)
        # 需要合并相邻的删除范围才能正确重建
        reconstructed = apply_delete_ranges(text, ranges)
        # 验证重建后的可见文本一致
        assert extract_visible_text(reconstructed) == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
