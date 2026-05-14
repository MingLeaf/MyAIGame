# =============================================================
# ui/font_manager.py —— 字体管理器（中英文字体加载与缓存）
# =============================================================

import os
from typing import Dict, Tuple, Optional
import pygame

# 字体缓存
_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

# Windows 常见中文字体文件路径（按优先级排列）
_WIN_FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
    "C:/Windows/Fonts/msyhbd.ttc",     # 微软雅黑 Bold
    "C:/Windows/Fonts/simsun.ttc",     # 宋体
    "C:/Windows/Fonts/simhei.ttf",     # 黑体
    "C:/Windows/Fonts/simkai.ttf",     # 楷体
    "C:/Windows/Fonts/STZHONGS.TTF",   # 华文中宋
    "C:/Windows/Fonts/STKAITI.TTF",    # 华文楷体
    "C:/Windows/Fonts/SIMLI.TTF",      # 隶书
]

# macOS / Linux 常见中文字体
_UNIX_FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

# 项目自带字体目录（放在 assets/ui/fonts/ 下时可自动发现）
_ASSETS_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "fonts"
)

# pygame SysFont 中文备选名称
_SYS_FONT_NAMES = [
    "microsoftyahei",
    "microsoftyaheimicrosoftyaheiui",
    "simhei",
    "simsun",
    "notosanscjk",
    "noto sans cjk sc",
    "wenquanyizenhei",
]

# 首次成功加载的字体路径缓存（避免重复遍历）
_resolved_path: Optional[str] = None


def _find_font_path() -> Optional[str]:
    """查找系统可用的中文字体文件路径"""
    global _resolved_path
    if _resolved_path is not None:
        return _resolved_path

    # 1. 先找 assets/ui/fonts/ 目录下的 .ttf/.ttc 文件
    if os.path.isdir(_ASSETS_FONT_DIR):
        for fname in os.listdir(_ASSETS_FONT_DIR):
            if fname.lower().endswith((".ttf", ".ttc", ".otf")):
                _resolved_path = os.path.join(_ASSETS_FONT_DIR, fname)
                return _resolved_path

    # 2. Windows 系统字体
    for path in _WIN_FONT_PATHS:
        if os.path.isfile(path):
            _resolved_path = path
            return _resolved_path

    # 3. Unix/macOS 系统字体
    for path in _UNIX_FONT_PATHS:
        if os.path.isfile(path):
            _resolved_path = path
            return _resolved_path

    return None


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """
    获取支持中文的字体（带缓存）。

    优先顺序：
        1. assets/ui/fonts/ 目录下的自带字体
        2. Windows / macOS / Linux 系统中文字体文件
        3. pygame SysFont 中文字体名称
        4. pygame 默认字体（中文将显示为方块，作为最终保底）
    """
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    font: Optional[pygame.font.Font] = None

    # 尝试从字体文件加载
    path = _find_font_path()
    if path:
        try:
            # .ttc 为字体集合，需指定 index=0 加载第一个字体（通常是 Regular）
            font = pygame.font.Font(path, size)
            # 验证：尝试渲染一个中文字符，若宽度为 0 说明字体不含中文
            test_surf = font.render("测", True, (255, 255, 255))
            if test_surf.get_width() == 0:
                font = None   # 不支持中文，继续尝试
        except Exception:
            font = None

    # 退而求其次：SysFont 按名称匹配
    if font is None:
        sys_font_list = [f.lower() for f in pygame.font.get_fonts()]
        for name in _SYS_FONT_NAMES:
            if name.replace(" ", "") in [f.replace(" ", "") for f in sys_font_list]:
                try:
                    font = pygame.font.SysFont(name, size, bold=bold)
                    # 同样验证中文渲染
                    test_surf = font.render("测", True, (255, 255, 255))
                    if test_surf.get_width() > 0:
                        break
                    font = None
                except Exception:
                    font = None
                    continue

    # 最终保底：pygame 默认字体（中文会乱码，但至少不崩溃）
    if font is None:
        font = pygame.font.SysFont(None, size, bold=bold)

    _cache[key] = font
    return font


def clear_cache():
    """清除字体缓存（热重载使用）"""
    global _resolved_path
    _cache.clear()
    _resolved_path = None
