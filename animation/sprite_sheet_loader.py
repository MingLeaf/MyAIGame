# =============================================================
# animation/sprite_sheet_loader.py —— 精灵表切割与缓存
#
# 将一整张精灵表按行列切割为单个帧 Surface，支持缓存加速。
# 后续替换美术资源时只需更新精灵表文件路径与行列参数。
# =============================================================
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import pygame

from utils.resource_cache import load_image


class SpriteSheetLoader:
    """
    精灵表切割器。

    用法：
        loader = SpriteSheetLoader()
        frames = loader.load("assets/sprites/player_run.png",
                             rows=1, cols=8,
                             frame_width=64, frame_height=64)

    缓存：
        同一文件路径 + 相同切割参数命中缓存，避免重复切割。
        调用 clear_cache() 可强制清空（资源热重载时使用）。

    接口（未来替换精灵表）：
        loader.replace_sheet(name, new_path, rows, cols, ...)
        或直接调用 load() 并让新参数覆盖旧缓存。
    """

    # 缓存 key → frame 列表
    _cache: Dict[str, List[pygame.Surface]] = {}

    def __init__(self):
        pass

    # ----------------------------------------------------------------
    # 加载与切割
    # ----------------------------------------------------------------

    def load(self,
             path: str,
             rows: int = 1,
             cols: int = 1,
             frame_width: int = 0,
             frame_height: int = 0,
             margin_x: int = 0,
             margin_y: int = 0,
             spacing_x: int = 0,
             spacing_y: int = 0,
             colorkey: Optional[Tuple[int, int, int]] = None,
             scale: float = 1.0) -> List[pygame.Surface]:
        """
        从精灵表加载切割后的帧列表。

        :param path:         精灵表文件路径（相对于项目根或绝对路径）
        :param rows:         行数
        :param cols:         列数
        :param frame_width:  每帧宽度（0=自动计算 总宽/cols）
        :param frame_height: 每帧高度（0=自动计算 总高/rows）
        :param margin_x:     起始水平边距
        :param margin_y:     起始垂直边距
        :param spacing_x:    帧间水平间距
        :param spacing_y:    帧间垂直间距
        :param colorkey:     透明色 (R,G,B)，None 则保持原图透明
        :param scale:        缩放倍率
        :return:             Surface 列表
        """
        cache_key = self._make_cache_key(
            path, rows, cols, frame_width, frame_height,
            margin_x, margin_y, spacing_x, spacing_y, colorkey, scale,
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        sheet = load_image(path)
        if sheet is None:
            # 图片不存在时返回空列表（静默兜底，让调用方用占位图）
            return []

        pw, ph = sheet.get_width(), sheet.get_height()

        fw = frame_width if frame_width > 0 else (pw - margin_x - spacing_x * (cols - 1)) // cols
        fh = frame_height if frame_height > 0 else (ph - margin_y - spacing_y * (rows - 1)) // rows

        frames: List[pygame.Surface] = []
        for row in range(rows):
            for col in range(cols):
                x = margin_x + col * (fw + spacing_x)
                y = margin_y + row * (fh + spacing_y)
                if x + fw > pw or y + fh > ph:
                    continue  # 超出精灵表范围则跳过

                frame = sheet.subsurface((x, y, fw, fh)).copy()

                if colorkey is not None:
                    frame.set_colorkey(colorkey)
                    frame = frame.convert_alpha()

                if scale != 1.0:
                    nw = max(1, int(fw * scale))
                    nh = max(1, int(fh * scale))
                    frame = pygame.transform.scale(frame, (nw, nh))

                frames.append(frame)

        self._cache[cache_key] = frames
        return frames

    # ----------------------------------------------------------------
    # 替换与查询
    # ----------------------------------------------------------------

    def replace_sheet(self,
                      cache_key_or_path: str,
                      path: str,
                      rows: int = 1,
                      cols: int = 1,
                      frame_width: int = 0,
                      frame_height: int = 0,
                      margin_x: int = 0,
                      margin_y: int = 0,
                      spacing_x: int = 0,
                      spacing_y: int = 0,
                      colorkey: Optional[Tuple[int, int, int]] = None,
                      scale: float = 1.0) -> List[pygame.Surface]:
        """
        强制替换某张精灵表的缓存——用于热重载美术资源。

        调用后所有持有旧帧引用的 Animator 需要重新调用 load()
        或手动刷新 AnimationClip.frames。
        """
        new_key = self._make_cache_key(
            path, rows, cols, frame_width, frame_height,
            margin_x, margin_y, spacing_x, spacing_y, colorkey, scale,
        )
        # 清除可能匹配的旧 key
        keys_to_clear = [k for k in self._cache if path in k]
        for k in keys_to_clear:
            del self._cache[k]
        # 重新加载
        return self.load(path, rows, cols, frame_width, frame_height,
                         margin_x, margin_y, spacing_x, spacing_y,
                         colorkey, scale)

    def has(self, path: str) -> bool:
        """检查路径对应的精灵表是否已在缓存中（部分匹配）。"""
        return any(path in k for k in self._cache)

    @classmethod
    def clear_cache(cls) -> None:
        """清空全部缓存（场景切换 / 资源热重载）。"""
        cls._cache.clear()

    @classmethod
    def cache_size(cls) -> int:
        """当前缓存的精灵表数量。"""
        return len(cls._cache)

    # ----------------------------------------------------------------
    # 内部工具
    # ----------------------------------------------------------------

    @staticmethod
    def _make_cache_key(path: str, rows: int, cols: int,
                        fw: int, fh: int,
                        mx: int, my: int, sx: int, sy: int,
                        ck: Optional[Tuple], scale: float) -> str:
        return f"{path}|r{rows}c{cols}|{fw}x{fh}|m{mx},{my}|s{sx},{sy}|ck{ck}|sc{scale:.2f}"

    def __repr__(self) -> str:
        return f"<SpriteSheetLoader cached={len(self._cache)}>"
