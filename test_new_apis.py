#!/usr/bin/env python3
"""
测试新增的API端点
"""

import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

def test_api_endpoint(endpoint_name, url, params=None):
    """测试API端点"""
    try:
        if params:
            response = requests.get(f"{API_BASE_URL}{url}", params=params, timeout=30)
        else:
            response = requests.get(f"{API_BASE_URL}{url}", timeout=30)

        print(f"✅ {endpoint_name}: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if endpoint_name == "视频缩略图":
                print(f"   缩略图数量: {len(data.get('data', []))}")
                if data.get('data'):
                    print(f"   最佳缩略图: {data['data'][0].get('resolution', 'N/A')}")
            elif endpoint_name == "字幕列表":
                data_content = data.get('data', {})
                print(f"   手动字幕: {len(data_content.get('subtitles', {}))} 种语言")
                print(f"   自动字幕: {len(data_content.get('automatic_captions', {}))} 种语言")
                if data_content.get('available_languages'):
                    print(f"   可用语言: {', '.join(data_content.get('available_languages', [])[:5])}...")
            elif endpoint_name == "视频详情":
                data_content = data.get('data', {})
                basic = data_content.get('basic_info', {})
                thumbs = data_content.get('thumbnails', {})
                subs = data_content.get('subtitles', {})
                print(f"   标题: {basic.get('title', 'N/A')}")
                print(f"   时长: {basic.get('duration', 'N/A')} 秒")
                print(f"   缩略图数量: {thumbs.get('count', 0)}")
                print(f"   字幕语言数: {len(subs.get('available_languages', []))}")

        return response.status_code == 200

    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name}: 连接失败 - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ {endpoint_name}: JSON解析失败 - {e}")
        return False
    except Exception as e:
        print(f"❌ {endpoint_name}: 其他错误 - {e}")
        return False

def main():
    print("开始测试新增的API端点...")
    print(f"测试视频: {TEST_VIDEO_URL}")
    print(f"API地址: {API_BASE_URL}")
    print("=" * 50)

    tests = [
        ("视频缩略图", "/thumbnails", {"url": TEST_VIDEO_URL}),
        ("字幕列表", "/subtitles", {"url": TEST_VIDEO_URL}),
        ("视频详情", "/video-details", {"url": TEST_VIDEO_URL}),
    ]

    success_count = 0
    total_count = len(tests)

    for test_name, endpoint, params in tests:
        print(f"\n🔍 测试 {test_name}...")
        if test_api_endpoint(test_name, endpoint, params):
            success_count += 1

    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")

    if success_count == total_count:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查API服务是否正常运行")

    # 测试字幕下载（需要特定语言）
    print(f"\n🔍 测试字幕下载...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/subtitle",
            params={"url": TEST_VIDEO_URL, "language": "en", "subtitle_format": "srt"},
            timeout=30
        )
        if response.status_code == 200:
            print("✅ 字幕下载: 成功")
            print(f"   文件大小: {len(response.content)} 字节")
        else:
            print(f"❌ 字幕下载: {response.status_code}")
    except Exception as e:
        print(f"❌ 字幕下载: 失败 - {e}")

    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)