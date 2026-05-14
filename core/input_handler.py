# =============================================================
# core/input_handler.py —— 统一输入管理器（键盘 / 手柄 / 鼠标）
# =============================================================

import pygame
from typing import Optional, Dict, Set, Tuple


# -------------------------------------------------------
# 默认键位映射（可在 settings 中修改）
# -------------------------------------------------------
DEFAULT_KEY_MAP: Dict[str, int] = {
    # 移动
    "move_left":    pygame.K_a,
    "move_right":   pygame.K_d,
    "move_up":      pygame.K_w,
    "move_down":    pygame.K_s,

    # 战斗
    "attack_light": pygame.K_j,
    "attack_heavy": pygame.K_k,
    "roll":         pygame.K_LSHIFT,   # 翻滚改为左 Shift
    "block":        pygame.K_l,
    "weapon_art":   pygame.K_u,

    # 交互
    "interact":     pygame.K_f,
    "use_item":     pygame.K_q,

    # 菜单
    "pause":        pygame.K_ESCAPE,
    "inventory":    pygame.K_i,
    "jump":         pygame.K_SPACE,    # 跳跃独占 Space

    # 调试
    "debug_toggle": pygame.K_F3,
}


class InputHandler:
    """
    统一输入管理器。
    每帧调用 update() 刷新输入状态。
    提供 is_pressed / just_pressed / just_released 三种查询。
    """

    def __init__(self, key_map: Optional[Dict[str, int]] = None):
        self._key_map: Dict[str, int] = dict(key_map or DEFAULT_KEY_MAP)

        # 当前帧按键状态（pygame.key.get_pressed() 的缓存）
        self._keys_held = None

        # 本帧新按下的键集合
        self._just_pressed:  Set[int] = set()
        # 本帧刚释放的键集合
        self._just_released: Set[int] = set()

        # 鼠标
        self._mouse_pos:           Tuple[int, int] = (0, 0)
        self._mouse_just_pressed:  Set[int] = set()
        self._mouse_held:          Set[int] = set()
        self._mouse_just_released: Set[int] = set()

        # 文字输入缓冲（给对话框等使用）
        self._text_input: str = ""

    # ---- 每帧刷新 ----

    def update(self, events: list):
        """每帧传入 pygame.event.get() 结果，刷新输入状态"""
        self._just_pressed.clear()
        self._just_released.clear()
        self._mouse_just_pressed.clear()
        self._mouse_just_released.clear()
        self._text_input = ""

        for event in events:
            if event.type == pygame.KEYDOWN:
                self._just_pressed.add(event.key)
            elif event.type == pygame.KEYUP:
                self._just_released.add(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_just_pressed.add(event.button)
                self._mouse_held.add(event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._mouse_just_released.add(event.button)
                self._mouse_held.discard(event.button)
            elif event.type == pygame.TEXTINPUT:
                self._text_input += event.text

        self._keys_held = pygame.key.get_pressed()
        self._mouse_pos = pygame.mouse.get_pos()

    # ---- 键盘查询（按动作名） ----

    def is_pressed(self, action: str) -> bool:
        """持续按住"""
        key = self._key_map.get(action)
        if key is None or self._keys_held is None:
            return False
        return bool(self._keys_held[key])

    def just_pressed(self, action: str) -> bool:
        """本帧刚按下"""
        key = self._key_map.get(action)
        return key in self._just_pressed if key else False

    def just_released(self, action: str) -> bool:
        """本帧刚释放"""
        key = self._key_map.get(action)
        return key in self._just_released if key else False

    # ---- 原始键码查询 ----

    def is_key_pressed(self, keycode: int) -> bool:
        return bool(self._keys_held[keycode]) if self._keys_held else False

    def key_just_pressed(self, keycode: int) -> bool:
        return keycode in self._just_pressed

    def key_just_released(self, keycode: int) -> bool:
        return keycode in self._just_released

    # ---- 鼠标查询 ----

    @property
    def mouse_pos(self) -> Tuple[int, int]:
        return self._mouse_pos

    def mouse_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_held

    def mouse_just_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_just_pressed

    def mouse_just_released(self, button: int = 1) -> bool:
        return button in self._mouse_just_released

    # ---- 方向轴（[-1, 0, 1]） ----

    @property
    def axis_x(self) -> int:
        """水平输入轴：左 -1 / 无 0 / 右 +1"""
        left  = self.is_pressed("move_left")
        right = self.is_pressed("move_right")
        return int(right) - int(left)

    @property
    def axis_y(self) -> int:
        """纵深输入轴：上 -1 / 无 0 / 下 +1"""
        up   = self.is_pressed("move_up")
        down = self.is_pressed("move_down")
        return int(down) - int(up)

    # ---- 文字输入 ----

    @property
    def text_input(self) -> str:
        return self._text_input

    # ---- 键位重映射 ----

    def remap(self, action: str, new_key: int):
        self._key_map[action] = new_key

    def get_key(self, action: str) -> Optional[int]:
        return self._key_map.get(action)

# 全局单例
input_handler = InputHandler()
