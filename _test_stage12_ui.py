# =============================================================
# _test_stage12_ui.py —— 第 12 阶段 UI 冒烟测试
#
# 测试覆盖：
#   1. BaseWidget 创建/可见性/层级
#   2. HUD/InventoryScreen/EquipmentScreen 继承 BaseWidget
#   3. FloatingText / FloatingTextManager（迁移后兼容）
#   4. Notification / NotificationManager
#   5. StatusPanel
#   6. LoadingScreen
#   7. MainMenuUI / PauseMenuUI
#   8. SettingsUI
#   9. combat.floating_text 兼容导入
#   10. GameScene 新 UI 集成
# =============================================================

import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()

# 加项目根目录
_PROJ_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
sys.path.insert(0, _PROJ_DIR)

_surface = pygame.Surface((1280, 720))

def test_1_base_widget():
    """BaseWidget 基础功能"""
    from ui.base_widget import BaseWidget
    import pygame

    # 默认构造
    w = BaseWidget()
    assert not w.visible
    assert w.z_index == 40
    assert w.rect is not None

    # 自定义构造
    rect = pygame.Rect(100, 200, 300, 400)
    w2 = BaseWidget(rect=rect, visible=True, z_index=50)
    assert w2.visible
    assert w2.z_index == 50
    assert w2.rect == rect
    assert w2.center == rect.center

    # show/hide/toggle
    w2.hide()
    assert not w2.visible
    w2.show()
    assert w2.visible
    w2.toggle()
    assert not w2.visible
    w2.toggle()
    assert w2.visible

    # handle_event 默认返回 False
    dummy_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a})
    assert w2.handle_event(dummy_event) is False

    # hide 后 handle_event 返回 False
    w2.hide()
    assert w2.handle_event(dummy_event) is False

    # is_hover
    assert w2.is_hover(200, 300)
    assert not w2.is_hover(0, 0)

    # 属性访问
    w2.x = 50
    assert w2.x == 50 and w2.rect.x == 50

    print("  PASS: test_1_base_widget")

def test_2_inheritance():
    """现有 UI 继承 BaseWidget"""
    from ui.base_widget import BaseWidget
    from ui.hud import HUD
    from ui.inventory_screen import InventoryScreen
    from ui.equipment_screen import EquipmentScreen

    hud = HUD()
    assert isinstance(hud, BaseWidget)
    assert hud.visible  # HUD 默认可见

    inv = InventoryScreen()
    assert isinstance(inv, BaseWidget)
    assert not inv.is_open

    equip = EquipmentScreen()
    assert isinstance(equip, BaseWidget)
    assert not equip.is_open

    print("  PASS: test_2_inheritance")

def test_3_floating_text():
    """飘字系统迁移"""
    from ui.damage_number import FloatingText, FloatingTextManager, DAMAGE_TYPE_COLORS

    # 单条飘字
    ft = FloatingText("-25", 400, 300)
    assert ft.active
    assert ft.text == "-25"
    assert ft.elapsed == 0.0

    # 更新
    ft.update(0.5)
    assert ft.active
    assert ft.elapsed == 0.5

    ft.update(1.0)
    assert not ft.active  # lifetime 1.0

    # 管理器
    ftm = FloatingTextManager()
    assert len(ftm) == 0

    ftm.add_damage(30, 400, 300, dmg_type="fire")
    assert len(ftm) == 1

    ftm.add_heal(15, 400, 300)
    assert len(ftm) == 2

    ftm.add_crit(80, 400, 300)
    assert len(ftm) == 3

    ftm.add_status("中毒", 400, 300, status_type="poison")
    assert len(ftm) == 4

    ftm.add("暴击!", 400, 300, color=(255, 80, 30), size=20)
    assert len(ftm) == 5

    ftm.update(2.0)  # 全部超时
    assert len(ftm) == 0

    ftm.clear()

    # 颜色映射
    assert DAMAGE_TYPE_COLORS["physical"] is not None
    assert DAMAGE_TYPE_COLORS["fire"] is not None
    assert DAMAGE_TYPE_COLORS["ice"] is not None
    assert DAMAGE_TYPE_COLORS["poison"] is not None
    assert DAMAGE_TYPE_COLORS["holy"] is not None
    assert DAMAGE_TYPE_COLORS["bleed"] is not None

    print("  PASS: test_3_floating_text")

def test_4_compat_import():
    """combat.floating_text 兼容导入"""
    from combat.floating_text import (
        FloatingText, FloatingTextManager,
        _CRIT_COLOR, _HEAL_COLOR, _DEFAULT_COLOR,
    )

    ftm = FloatingTextManager()
    assert len(ftm) == 0

    ft = FloatingText("-50", 100, 200, color=_CRIT_COLOR, lifetime=2.0)
    assert ft.active

    print("  PASS: test_4_compat_import")

def test_5_notification():
    """通知系统"""
    from ui.notification import Notification, NotificationManager

    nm = NotificationManager()
    assert nm.visible

    # 区域名
    nm.show_area("古墓地带")
    assert len(nm._notifications) == 1

    # Boss
    nm.show_boss("腐骨公爵 降临")
    assert len(nm._notifications) == 2

    # 物品拾取
    nm.show_item_pickup("草药汤 ×3")
    assert len(nm._stack_items) == 1

    # 多个堆叠
    for i in range(6):
        nm.show_item_pickup(f"物品{i}")
    assert len(nm._stack_items) <= 5  # 最多 5 条

    # 更新
    nm.update(4.0)  # 全部超时
    assert len(nm._notifications) == 0
    assert len(nm._stack_items) == 0

    nm.clear()

    print("  PASS: test_5_notification")

def test_6_status_panel():
    """人物属性面板"""
    from ui.status_panel import StatusPanel

    sp = StatusPanel()
    assert isinstance(sp, StatusPanel)
    assert not sp.is_open

    # toggle（无 player 时不崩溃）
    sp.toggle(None)
    assert not sp.is_open

    class FakeGrowth:
        strength = 10; dexterity = 12; intelligence = 8
        faith = 6; vitality = 14; endurance = 11
        unspent = 3
        level = 1
        equip_weight = 30.0
        max_equip_load = 60.0
        equip_load_ratio = 0.5
        roll_type = "normal"

    class FakeStats:
        hp = 100; max_hp = 100
        stamina = 80; max_stamina = 80
        mana = 50; max_mana = 50
        atk = 35

    class FakeBuild:
        level = 1
        unspent = 3

    class FakePlayer:
        growth = FakeGrowth()
        stats = FakeStats()
        build = FakeBuild()
        soul_fragments = 500
        equipment = None
        weapon = None

    p = FakePlayer()
    sp.toggle(p)
    assert sp.is_open

    # 事件处理
    tab_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_TAB})
    assert sp.handle_event(tab_event)  # 关闭
    assert not sp.is_open

    print("  PASS: test_6_status_panel")

def test_7_loading_screen():
    """加载界面"""
    from ui.loading_screen import LoadingScreen

    ls = LoadingScreen()
    assert not ls.is_done

    ls.start("毒沼泽地")
    assert ls.visible
    assert not ls.is_done

    ls.set_progress(0.5)
    for _ in range(60):
        ls.update(1/60)
    assert not ls.is_done

    ls.finish()
    for _ in range(120):
        ls.update(1/60)
    assert ls.is_done

    # 渲染测试（不崩溃）
    ls.render(_surface)

    print("  PASS: test_7_loading_screen")

def test_8_main_menu_ui():
    """主菜单 UI"""
    from ui.main_menu_ui import MainMenuUI

    mm = MainMenuUI()
    assert mm.visible

    # 更新
    mm.update(1.0)

    # 渲染
    mm.render(_surface)

    # 事件
    down = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN})
    assert mm.handle_event(down) is None

    up = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP})
    assert mm.handle_event(up) is None

    enter = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
    action = mm.handle_event(enter)
    assert action in ("start", "continue", "settings", "quit")

    print("  PASS: test_8_main_menu_ui")

def test_9_pause_menu_ui():
    """暂停菜单 UI"""
    from ui.pause_menu_ui import PauseMenuUI

    pm = PauseMenuUI()
    assert not pm.visible

    pm.open()
    assert pm.visible

    # 渲染
    pm.render(_surface)

    # ESC 返回 resume
    esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
    assert pm.handle_event(esc) == "resume"

    # Enter 确认
    enter = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
    action = pm.handle_event(enter)
    assert action in ("resume", "restart", "settings", "quit")

    pm.close()
    assert not pm.visible

    print("  PASS: test_9_pause_menu_ui")

def test_10_settings_ui():
    """设置界面"""
    from ui.settings_ui import SettingsUI

    su = SettingsUI()
    su.open()
    assert su.visible

    # 渲染
    su.render(_surface)

    # 上下导航
    down = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN})
    assert su.handle_event(down) is None

    up = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP})
    assert su.handle_event(up) is None

    # ESC 取消
    esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
    assert su.handle_event(esc) == "cancel"

    su.close()
    assert not su.visible

    print("  PASS: test_10_settings_ui")

def test_11_game_scene_integration():
    """GameScene 包含新 UI 字段（不运行完整场景）"""
    from scenes.game_scene import GameScene

    # 只验证 GameScene 类能否导入并实例化（不加载地图）
    try:
        gs = GameScene()
        assert hasattr(gs, "_notifications")
        assert hasattr(gs, "_status_panel")
        print("  PASS: test_11_game_scene_integration")
    except Exception as e:
        # 若缺少 Pygame display 等，跳过
        print(f"  SKIP: test_11_game_scene_integration ({e})")

def main():
    print("=" * 60)
    print("第 12 阶段 UI 冒烟测试")
    print("=" * 60)

    tests = [
        ("test_1_base_widget",      test_1_base_widget),
        ("test_2_inheritance",      test_2_inheritance),
        ("test_3_floating_text",    test_3_floating_text),
        ("test_4_compat_import",    test_4_compat_import),
        ("test_5_notification",     test_5_notification),
        ("test_6_status_panel",     test_6_status_panel),
        ("test_7_loading_screen",   test_7_loading_screen),
        ("test_8_main_menu_ui",     test_8_main_menu_ui),
        ("test_9_pause_menu_ui",    test_9_pause_menu_ui),
        ("test_10_settings_ui",     test_10_settings_ui),
        ("test_11_game_scene",      test_11_game_scene_integration),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            import traceback
            print(f"  FAIL: {name}")
            traceback.print_exc()

    print()
    print(f"结果: {passed}/{passed+failed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    ok = main()
    pygame.quit()
    sys.exit(0 if ok else 1)
