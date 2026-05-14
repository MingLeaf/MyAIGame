# =============================================================
# core/game.py —— 游戏主类，管理主循环、场景切换、全局状态
# =============================================================

import sys
import logging
import pygame

from config import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS_TARGET,
                    GAME_TITLE, VSYNC, DEBUG_MODE)
from core.clock         import GameClock
from core.renderer      import Renderer
from core.scene_manager import scene_manager
from core.input_handler import input_handler
from core.event_manager import event_manager
import utils.debug as debug

logger = logging.getLogger(__name__)


class Game:
    """
    游戏主类。
    负责：
    - pygame 初始化 / 反初始化
    - 主循环（事件 → 更新 → 渲染）
    - 全局资源（屏幕、时钟、渲染器）管理
    - 将第一个场景压入 SceneManager
    """

    def __init__(self):
        self._setup_logging()
        self._init_pygame()

        self.clock    = GameClock(FPS_TARGET)
        self.renderer = Renderer(self._screen)
        self._running = False

        # 调试用小字体
        self._debug_font = pygame.font.SysFont("monospace", 14, bold=False)

    # ---- 初始化 ----

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG if DEBUG_MODE else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def _init_pygame(self):
        pygame.init()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        pygame.display.set_caption(GAME_TITLE)

        flags = pygame.DOUBLEBUF
        if VSYNC:
            flags |= pygame.SCALED

        self._screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), flags
        )
        logger.info("pygame 初始化完成，分辨率 %dx%d", SCREEN_WIDTH, SCREEN_HEIGHT)

    # ---- 主循环 ----

    def run(self, first_scene=None):
        """
        启动主循环。
        :param first_scene: 首个场景实例（通常是主菜单或测试场景）
        """
        if first_scene is not None:
            scene_manager.push(first_scene)
        else:
            # 没有传入场景时，使用内置空白测试场景
            from scenes.base_scene import BaseScene
            scene_manager.push(BaseScene())

        self._running = True
        logger.info("游戏主循环启动")

        while self._running:
            dt = self.clock.tick()

            # 1. 收集事件
            events = pygame.event.get()

            # 2. 检测退出
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False

            # 3. 更新输入
            input_handler.update(events)

            # 4. 调试快捷键
            if input_handler.key_just_pressed(pygame.K_F3):
                debug.enabled     = not debug.enabled
                debug.show_hitbox = debug.enabled

            # 5. 场景事件处理
            scene_manager.handle_events(events)

            # 6. 场景逻辑更新
            debug.clear_lines()
            scene_manager.update(dt)

            # 7. 延迟事件总线刷新
            event_manager.flush()

            # 8. 渲染
            self.renderer.begin()
            scene_manager.render(self.renderer)
            self.renderer.end()

            # 9. 调试 HUD（直接绘制到屏幕，不经过层系统）
            if debug.enabled:
                debug.render(self._screen, self._debug_font, self.clock.fps)
                pygame.display.flip()   # 二次 flip（仅调试帧用）

            # 10. 帧末：处理挂起的场景操作
            scene_manager.apply_pending()

            # 场景栈空时退出
            if scene_manager.is_empty():
                self._running = False

        self._shutdown()

    # ---- 退出 ----

    def _shutdown(self):
        logger.info("游戏退出，共运行 %.1f 秒，%d 帧",
                    self.clock.total_time, self.clock.frame_count)
        pygame.quit()
        sys.exit(0)
