"""
Preview Processor 的单元测试

重点测试删除范围验证逻辑
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.preview_processor import (
    _validate_edited_script,
    _get_pure_text,
)


class TestGetPureText:
    """测试 _get_pure_text 函数"""
    
    def test_remove_all_braces(self):
        """测试移除所有大括号"""
        script = "这是{删除}保留{内容}"
        result = _get_pure_text(script)
        assert result == "这是删除保留内容"
    
    def test_no_braces(self):
        """测试没有大括号"""
        script = "这是纯文本"
        result = _get_pure_text(script)
        assert result == "这是纯文本"
    
    def test_nested_braces(self):
        """测试嵌套大括号"""
        script = "这是{{嵌套}}保留"
        result = _get_pure_text(script)
        assert result == "这是嵌套保留"
    
    def test_empty_script(self):
        """测试空字符串"""
        script = ""
        result = _get_pure_text(script)
        assert result == ""


class TestValidateEditedScript:
    """测试 _validate_edited_script 函数"""
    
    def test_same_content_with_different_deletes(self):
        """测试相同内容不同删除范围（合法）"""
        original = "这是{要删除的内容}保留的内容"
        edited = "这是要删除的{内容保留}的内容"
        # 两者纯文本都是: "这是要删除的内容保留的内容"
        _validate_edited_script(edited, original)  # 不应抛出异常
    
    def test_restore_deleted_content(self):
        """测试反删除线操作（合法）"""
        original = "这是{删除内容}保留"
        edited = "这是删除内容保留"  # 反删除，去掉大括号
        # 两者纯文本都是: "这是删除内容保留"
        _validate_edited_script(edited, original)  # 不应抛出异常
    
    def test_add_delete_to_content(self):
        """测试添加删除线（合法）"""
        original = "这是删除内容保留"
        edited = "这是{删除内容}保留"  # 添加大括号
        # 两者纯文本都是: "这是删除内容保留"
        _validate_edited_script(edited, original)  # 不应抛出异常
    
    def test_modified_content_illegal(self):
        """测试修改正文内容（非法）"""
        original = "这是{删除}保留"
        edited = "这是{修改}保留"  # 改变了正文内容
        with pytest.raises(ValueError) as exc_info:
            _validate_edited_script(edited, original)
        assert "正文内容与原始内容不一致" in str(exc_info.value)
    
    def test_added_content_illegal(self):
        """测试添加新内容（非法）"""
        original = "这是{删除}保留"
        edited = "这是{删除}保留新增"  # 添加了新内容
        with pytest.raises(ValueError) as exc_info:
            _validate_edited_script(edited, original)
        assert "正文内容与原始内容不一致" in str(exc_info.value)
    
    def test_deleted_content_illegal(self):
        """测试直接删除正文字符（非法）"""
        original = "这是{删除}保留内容"
        edited = "这是{删除}保留"  # 直接删除了"内容"
        with pytest.raises(ValueError) as exc_info:
            _validate_edited_script(edited, original)
        assert "正文内容与原始内容不一致" in str(exc_info.value)
    
    def test_unbalanced_braces_illegal(self):
        """测试大括号不匹配（非法）"""
        original = "这是{删除}保留"
        edited = "这是{删除保留"  # 缺少右大括号
        with pytest.raises(ValueError) as exc_info:
            _validate_edited_script(edited, original)
        assert "大括号格式不合法" in str(exc_info.value)
    
    def test_reorder_content_illegal(self):
        """测试改变字符顺序（非法）"""
        original = "这是{删除}保留内容"
        edited = "这是{删除}内容保留"  # 改变了顺序
        with pytest.raises(ValueError) as exc_info:
            _validate_edited_script(edited, original)
        assert "正文内容与原始内容不一致" in str(exc_info.value)


class TestValidateEditedScriptEdgeCases:
    """测试边界情况"""
    
    def test_empty_to_empty(self):
        """测试空字符串到空字符串"""
        _validate_edited_script("", "")  # 不应抛出异常
    
    def test_multiple_deletes_restore(self):
        """测试多个删除全部恢复"""
        original = "{删除1}保留{删除2}"
        edited = "删除1保留删除2"  # 全部反删除
        _validate_edited_script(edited, original)  # 不应抛出异常
    
    def test_multiple_deletes_add_more(self):
        """测试添加更多删除标记"""
        original = "删除1保留删除2"
        edited = "{删除1}保{留}删除2"  # 添加更多删除标记
        _validate_edited_script(edited, original)  # 不应抛出异常


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
