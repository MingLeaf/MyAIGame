# =============================================================
# main.py —— 程序入口，初始化游戏并启动主循环
# =============================================================

from core.game import Game
from scenes.main_menu_scene import MainMenuScene


def main():
    game = Game()
    game.run(first_scene=MainMenuScene())


if __name__ == "__main__":
    main()
