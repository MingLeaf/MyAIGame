# =============================================================
# config.py —— 全局常量配置
# =============================================================

import os

# ------- 版本 -------
GAME_TITLE   = "烬土传说"
GAME_VERSION = "0.1.0"

# ------- 窗口 / 渲染 -------
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS_TARGET    = 60
VSYNC         = False

# ------- 路径根目录 -------
ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR  = os.path.join(ROOT_DIR, "assets")
DATA_DIR    = os.path.join(ROOT_DIR, "data")
SAVE_DIR    = os.path.join(ROOT_DIR, "save", "slots")

# ------- 物理 -------
GRAVITY         = 900       # 像素/秒²
MAX_FALL_SPEED  = 1200      # 像素/秒，最大下落速度
JUMP_FORCE      = -480      # 像素/秒，跳跃初速度（向上为负）

# ------- 摄像机 -------
CAMERA_SMOOTH   = 8.0       # 摄像机跟随平滑系数

# ------- 图层深度（Z-order） -------
LAYER_BACKGROUND  = 0
LAYER_GROUND      = 10
LAYER_ENTITY      = 20
LAYER_PROJECTILE  = 25
LAYER_FOREGROUND  = 30
LAYER_PARTICLE    = 35
LAYER_UI          = 40

# ------- 调试 -------
DEBUG_MODE         = False   # 全局调试开关（按 F3 切换）
DEBUG_SHOW_HITBOX  = False   # 显示碰撞框
DEBUG_SHOW_FPS     = False   # 显示帧率
