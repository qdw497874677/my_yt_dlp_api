#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件名长度限制功能
"""

# 从main.py导入函数
from main import NormalizeString, create_safe_filename

def test_normalize_string():
    """测试NormalizeString函数"""
    print("=== 测试 NormalizeString 函数 ===")
    
    # 测试正常长度的字符串
    test1 = "正常长度的视频标题"
    result1 = NormalizeString(test1)
    print(f"输入: {test1}")
    print(f"输出: {result1}")
    print(f"长度: {len(result1)}")
    print()
    
    # 测试包含特殊字符的字符串
    test2 = "视频标题/包含*特殊?字符<>|"
    result2 = NormalizeString(test2)
    print(f"输入: {test2}")
    print(f"输出: {result2}")
    print(f"长度: {len(result2)}")
    print()
    
    # 测试超长字符串
    test3 = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的视频标题，用来测试文件名长度限制功能是否能正常工作，它应该被截断到指定的长度范围内"
    result3 = NormalizeString(test3, 50)
    print(f"输入: {test3}")
    print(f"输出: {result3}")
    print(f"长度: {len(result3)}")
    print()

def test_create_safe_filename():
    """测试create_safe_filename函数"""
    print("=== 测试 create_safe_filename 函数 ===")
    
    # 测试正常情况
    title1 = "正常的视频标题"
    format1 = "bestvideo+bestaudio"
    ext1 = "mp4"
    result1 = create_safe_filename(title1, format1, ext1)
    print(f"标题: {title1}")
    print(f"格式: {format1}")
    print(f"扩展名: {ext1}")
    print(f"文件名: {result1}")
    print(f"长度: {len(result1)}")
    print()
    
    # 测试超长标题
    title2 = "这是一个超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级长的视频标题，包含了很多很多很多很多很多很多很多字符"
    format2 = "best"
    ext2 = "webm"
    result2 = create_safe_filename(title2, format2, ext2)
    print(f"标题: {title2}")
    print(f"格式: {format2}")
    print(f"扩展名: {ext2}")
    print(f"文件名: {result2}")
    print(f"长度: {len(result2)}")
    print()
    
    # 测试包含特殊字符的超长标题
    title3 = "【测试视频】这是一个包含/特殊*字符?的<超长>标题|用来测试文件名处理功能是否能够正确处理各种复杂情况，包括中文字符、特殊符号和长度限制等等等等等等等"
    format3 = "bestvideo+bestaudio/best"
    ext3 = "mkv"
    result3 = create_safe_filename(title3, format3, ext3)
    print(f"标题: {title3}")
    print(f"格式: {format3}")
    print(f"扩展名: {ext3}")  
    print(f"文件名: {result3}")
    print(f"长度: {len(result3)}")
    print()

if __name__ == "__main__":
    print("开始测试文件名长度限制功能...")
    print()
    
    try:
        test_normalize_string()
        test_create_safe_filename()
        print("✅ 所有测试完成，文件名长度限制功能正常工作！")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()