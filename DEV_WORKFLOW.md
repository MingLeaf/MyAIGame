# 烬土传说 · 开发工作流提示词集

> 本文档记录已完成工作 + 拆分剩余开发任务为可复制到不同窗口的提示词。
> 每段提示词都是「自包含」的：贴入新窗口即可让 AI 助手接续工作。

---

## 一、当前工程状态总结（截至第 9 阶段完成）

### 1.1 已完成阶段

| 阶段 | 名称 | 状态 |
|---|---|---|
| 第 1 阶段 | 工程基础（utils + core） | ✅ 完成 |
| 第 2 阶段 | 地图与物理（map + physics） | ✅ 完成 |
| 第 3 阶段 | 玩家基础（移动/跳跃/翻滚 + 状态机 + HUD） | ✅ 完成 |
| 第 4 阶段 | 战斗核心（伤害/状态异常/弹反/连段/抛射物） | ✅ 完成 |
| 第 5 阶段 | 武器系统（8 类武器 + 词条 + 战技 + 强化） | ✅ 完成 |
| 第 6 阶段 | 物品与背包系统（消耗品/套装/掉落/拾取） | ✅ 完成 |
| 第 7 阶段 | 敌人 AI 系统（7 类敌人 + 五态闭环 + 数据驱动） | ✅ 完成 |
| 第 8 阶段 | 游戏规则核心（灵魂碎片/死亡复活/营地/升级/强化/进度） | ✅ 完成 |
| 第 9 阶段 | Boss 系统（BaseBoss + 腐骨公爵 + 雾门 + 血条 + BossScene） | ✅ 完成 |

### 1.2 实际目录结构（已实现的关键模块）

```
core/        scene_manager / event_manager / camera / input_handler / clock / renderer / game
utils/       state_machine / json_loader / resource_cache / timer / debug / color / math_utils / rect_utils
physics/     gravity / collision_detector / movement_resolver / projectile
map/         tile / tile_map / collision_map / layer_renderer / platform / trap / transition_gate
             campfire / area / world_map
entities/
  player/    player / player_stats / growth_stats / player_states (含 Block 状态)
             player_combat / attack_hitbox (兼容包装) / player_inventory (PlayerInventory 别名)
  enemy/     base_enemy / enemy_ai (NEW Stage7) / enemy_states (兼容包装)
             enemy_stats（新增 alert_threshold/speed/decay 字段）
             enemy_spawner (NEW Stage7)
             types/{infantry, heavy_armor, undead, beast,
                   archer, mage, elite}（NEW Stage7，全部数据驱动）
             types/_data_loader（共享 JSON 加载工具）
combat/      damage_calculator / hit_resolver / floating_text / drop_system
             status_effect / status_manager
             hitbox / knockback / poise_system
             combo_system / parry_system
             status_effects (别名) / status_effect_manager (别名)
weapons/     base_weapon / sword / dagger / greatsword / holy_tome
             types/{spear, axe, bow, staff}
             affixes/{elemental_enchant, lifesteal, swift, armor_break, status_boost}
             weapon_art / weapon_upgrade
items/       item_base / consumable / weapon / armor / item_database / item_manager
             consumables/{heal_potion, mana_potion, stamina_potion, antidote,
                          buff_items, special_items, arrow}
             equipment/{set_bonus}
             special/{boss_soul, upgrade_material}
player/      inventory / equipment / player_build（旧版命名空间，沿用）
systems/     loot_system (Stage7)
             soul_fragment_system / respawn_system / campfire_system
             progression_system / upgrade_system / quest_system (NEW Stage8)
ui/          font_manager / hud / inventory_screen / equipment_screen
scenes/      base_scene / main_menu_scene / game_scene / pause_scene
data/
  maps/area_graveyard/{tilemap, enemy_spawns}.json (NEW Stage7)
  maps/world_config.json
  balance/{damage_formula, status_effect_values, loot_tables, level_curve, upgrade_cost}.json (level_curve/upgrade_cost NEW Stage8)
  weapons/upgrade_curve.json
  weapons/{sword,greatsword,dagger,spear,axe,staff,holy_tome,bow}_list.json
  items/{consumables, armors, upgrade_materials}.json
  entities/enemies/{infantry, heavy_armor, undead, beast,
                    archer, mage, elite}.json (NEW Stage7)
```

### 1.3 第 4 阶段重构亮点

1. **数据驱动落地**：伤害公式与状态异常数值已从 JSON 加载
2. **组件化解耦**：
   - `KnockbackComponent`（玩家+敌人共用击退）
   - `PoiseComponent`（韧性独立组件，EnemyStats 委托给它）
   - `BlockComponent` + `ParryWindow`（格挡 + 弹反窗口）
   - `ComboWindow` + `ComboChain`（攻击连段输入窗口）
   - `PlayerCombat`（玩家战斗组件，统一受击/格挡/弹反入口）
3. **新增交互**：按住 `L` 格挡，按下瞬间 0.18s 内被攻击触发弹反
4. **抛射物基础**：`physics/projectile.py` 已含 `Projectile / Arrow / MagicBall`

### 1.3.5 第 5 阶段实施摘要（武器系统补全）

1. **8 类武器全部就绪**
   - 已有：`Sword / Dagger / Greatsword / HolyTome`
   - 新增：`Spear（长矛）/ Axe（战斧）/ Bow（弓）/ Staff（法杖）`，位于 `weapons/types/`
   - `weapons/types/__init__.py` 提供 `WEAPON_REGISTRY` + `create_weapon(weapon_type)` 工厂
2. **词条系统（组合方式挂在 BaseWeapon 上）**
   - `WeaponAffix` 基类（含 `on_attach / on_detach / modify_attack` 钩子）
   - 5 类词条：`ElementalEnchant`（火/冰/雷/毒）`Lifesteal / Swift / ArmorBreak / StatusBoost`
   - `BaseWeapon._post_process()` 在 `get_light/heavy_attack` 末尾按顺序执行词条修饰
   - `AttackData` 新增字段：`armor_pierce / lifesteal / bonus_damage / burn_stack / freeze_stack / shock_stack`
3. **战技系统**
   - `WeaponArt` 基类：`mana_cost / cooldown / try_execute / _execute / _check_resources`
   - 已实装：`SpearCounterArt（盾突反击）`、`AxeShieldCrushArt（碎盾劈砍）`、`BowPiercingArrowArt（穿云箭）`、`StaffArcaneBarrageArt（魔法弹幕，5 颗 MagicBall）`
   - 通过 U 键 (`input_handler.weapon_art`) 触发：`Player._read_input` 检测后调用 `PlayerCombat.try_weapon_art(area)`
   - `Player.current_area` 字段供战技生成抛射物（GameScene 应在每帧 set，弓/法杖会自动写入 `area.projectiles`）
4. **武器强化系统**
   - `WeaponUpgrade` 类：`upgrade_to(weapon, level, route)` / `upgrade_one(weapon, route?)` / `calculate_params(level, route)` (preview)
   - 5 条路线：`none / sharp / heavy / blessed / elemental`
   - 数据：`data/weapons/upgrade_curve.json`（max_level=10，每级线性倍率）
   - `BaseWeapon.apply_upgrade()` 写入 `_upgrade_dmg_mult / _upgrade_poise_mult / _upgrade_bleed_mult / _upgrade_elem_override / _upgrade_bonus_dmg`，由 `_post_process` 应用
5. **数据驱动**
   - 8 个 `data/weapons/{type}_list.json`，每文件含 2~3 件武器变体（id/display_name/数值/稀有度/描述）
6. **集成与兼容性**
   - `BaseWeapon` 新增 `__init__`（旧 Sword/Dagger/... 子类无需改动，自动调用）
   - `Greatsword` 的 `get_light/heavy_attack` 重写已适配新强化倍率
   - `map.area.Area` 新增 `projectiles: List = []`
   - `PlayerCombat.update` 推进战技冷却；`PlayerCombat.try_weapon_art(area)` 提供统一触发接口
   - `_test_stage5_weapons.py` 冒烟测试覆盖：实例化 / 8 类武器 AttackData / 5 类词条 / 强化曲线 / 4 个战技 / JSON 加载 / Player 集成
   - 第 4 阶段集成测试 (`_test_stage4_integration.py`) 仍 100% 通过

### 1.3.6 第 6 阶段实施摘要（物品与背包系统补全）

1. **消耗品体系完整**：`items/consumables/` 下补齐 7 类消耗品
   - `HealPotion / ManaPotion / StaminaPotion / Antidote / BuffItem / SpecialItem / ArrowItem`
2. **特殊功能物品**：`items/special/{boss_soul, upgrade_material}` 完成；强化材料含 4 路线 + tier
3. **套装系统**：`items/equipment/set_bonus.py` 提供 `SetBonusManager`，3 套（骑士/游侠/法师）
4. **物品掉落 / 拾取链路**：`items/item_manager.py` 提供 `DroppedItem` 实体 + `spawn_drop / roll_and_spawn / try_pickup_all`
5. **数据驱动**：`data/items/{consumables, armors, upgrade_materials}.json`，`item_db` 启动时加载
6. **弓箭严格消耗**：`bow.py` 校验 ARROW_ITEM_ID 库存，无箭不发射、不能触发战技、派发 weapon_no_ammo 事件

### 1.3.7 第 7 阶段实施摘要（敌人 AI 系统扩展）

1. **7 类敌人全部就绪**（按 game_rule.md §4.3 定义）
   - 旧：`Infantry / HeavyArmor / Undead / Beast` 全部迁入 `entities/enemy/types/`
   - 新增：`Archer（弓箭手）/ Mage（法师）/ Elite（精英兵）`
   - `entities/enemy/types/__init__.py` 提供 `ENEMY_REGISTRY` + `create_enemy(category, x, y)` 工厂
2. **完整 5 态 AI**（`entities/enemy/enemy_ai.py`，旧 `enemy_states.py` 改为兼容包装）
   - `Idle/Patrol → Alert（警戒值累积）→ Chase → Attack → Return（回归出生点回血）`
   - `Hurt / Dead` 与原版一致；`base_enemy.register_default_states` 一次性挂载 7 态
   - `EnemyStats` 新增 `alert_threshold / alert_speed / alert_decay` 字段
   - `BaseEnemy` 在 Alert 状态头顶绘制黄色感叹号
3. **远程敌人**
   - Archer：`try_ranged_attack(dist)` 钩子接管 Chase；理想射距站定射 Arrow，玩家近身则后撤
   - Mage：长吟唱（默认 50 帧）→ 释放 MagicBall；吟唱期被打断 → `_reset_cast()` + `mage_cast_interrupted` 事件
   - 头顶吟唱条 / 弓瞄准线 / 精英技能扇形警告框 等可视化
4. **精英兵独特技能**（`Elite._SkillRunner`）
   - `charge_slash`（蓄力斩 1.8× 伤害）+ `sweep`（范围扫击 1.2× 伤害）
   - 每个技能独立 windup/active/cooldown + 独立全局 CD（`min_cd_sec`）
5. **数据驱动**
   - 7 个 `data/entities/enemies/{type}.json`：数值 / 渲染 / 远程 cast 配置 / 掉落表 ID
   - `data/balance/loot_tables.json`：全局掉落表（infantry_basic / archer_basic / elite_basic 等 7 个）
   - `entities/enemy/types/_data_loader.py` 统一加载 + 缓存
   - `EnemyStats.from_dict(data)` 工厂方法
6. **EnemySpawner**（`entities/enemy/enemy_spawner.py`）
   - 优先读 `data/maps/<area_id>/enemy_spawns.json`，缺失则回退到 `tilemap.json` 内的 `enemy_spawns`
   - 支持 `level` 字段（HP +20%/级，ATK +12%/级）+ `patrol_radius` 覆盖
   - `data/maps/area_graveyard/enemy_spawns.json` 配置 9 个敌人（按难度梯度：infantry/archer/beast/undead）
7. **掉落系统升级**
   - 新增 `systems/loot_system.py` 提供 `LootSystem.get_table / roll / spawn / spawn_for_enemy`
   - 与 `combat/drop_system.py` 兼容：仍接受 `List[DropEntry]`
   - `GameScene._on_enemy_dead` 改用 `LootSystem.spawn_for_enemy`
8. **抛射物管线打通**
   - `GameScene._update_projectiles(dt)`：每帧推进 `area.projectiles`，自动选择目标列表（玩家弹 → 敌人；敌弹 → 玩家），渲染加入第 4.5 层
9. **向后兼容**
   - `entities/enemy/{infantry,heavy_armor,undead,beast}.py` 改为 re-export 包装
   - `entities/enemy/enemy_states.py` re-export `enemy_ai` 全部符号
   - `BaseEnemy` 接口零变更；旧 `enemy.drop_table` 字段仍生效
10. **冒烟测试** `_test_stage7_enemies.py` 全部通过；第 4/5/6 阶段测试 100% 回归通过

### 1.3.8 第 7 阶段补充（玩家初始装备 + 地图重制）

1. **Player 初始装备发放**（`Player.grant_starting_kit()`）
   - 默认 `GIVE_STARTING_KIT=False`（避免单元测试受影响），`GameScene.on_enter` 显式调用
   - 装备：`sword_iron`（武器） + 4 件游侠轻甲 → 自动激活 `ranger` 套装效果（耐力恢复 +5/s + 翻滚无敌帧 +0.05s）
   - 背包：`heal_potion_small ×5 / heal_potion_large ×1 / mana_potion_basic ×3 / stamina_potion_basic ×2 / antidote_universal ×2 / buff_sharp_powder ×2 / arrow ×20 / poison_dart ×3`
   - 派 `player_starting_kit_granted` 事件供 UI 飘字
2. **古墓地图重制**（`data/maps/area_graveyard/tilemap.json` 80×22）
   - 物理参数计算：JUMP_FORCE=-480 + GRAVITY=900 → 最大跳跃高 128 px = 4 行；最大水平跳跃 256 px = 8 列
   - 平台分层规则：每一层与下方踏脚石垂直差 = 96 px (3 行)，水平偏移 ≤ 5 列
   - 11 个单向平台全部经测试可达（`_test_stage7_map_redesign.py [5]` 自动验证）
   - 5 个区段：A 起始营地 / B 废弃工坊 / C 墓室垂直爬升 / D 地下竞技场 / E 出口走廊
   - 3 个营地：cf_01 (col 7) / cf_02 (col 47) / cf_03 (col 73)
   - 13 个敌人按难度梯度从左到右递增（infantry → archer → undead → beast → mage）
   - 弓箭手 / 法师正确站在指定平台上（已 60 帧物理验证）
3. **冒烟测试**：`_test_stage7_map_redesign.py` 7 组验证全部通过

### 1.3.9 第 8 阶段实施摘要（游戏规则核心系统）

1. **灵魂碎片系统**（`systems/soul_fragment_system.py`）
   - `SoulFragmentSystem.grant_for_enemy(player, enemy)`：敌人死亡 → 按类型/等级倍率自动入账
   - `DeathRelic`：玩家死亡时在死亡位置生成脉动光球（含全部碎片），渲染多圈光晕
   - `create_death_relic` → 旧遗物自动消失；`try_pickup_relic` → 玩家走入半径捡回
   - 事件：`soul_fragments_changed` / `death_relic_spawned` / `death_relic_recovered`

2. **复活系统**（`systems/respawn_system.py`）
   - `RespawnSystem.handle_death(player, area)`：完整死亡→复活闭环
   - 流程：保留旧位置 → 查最近营地 → 传送玩家 → 恢复 HP/Mana/Stamina → 补消耗品 → 重置敌人 → 在旧位置创建遗物
   - 确保遗物在 `area.reload()` 之后创建，不被清除

3. **营地系统**（`systems/campfire_system.py`）
   - 激活时注册到全局（`CampfireSystem.activate`）
   - `rest(player, area)`：回满 HP/Mana/Stamina + 补满限定消耗品 + 重置全部敌人
   - 补满逻辑遍历 `_REFILLABLE_IDS` 集合，从 `item_db` 读 `max_stack`
   - `get_transport_targets(current_id)`：返回可传送营地列表

4. **升级系统**（`systems/progression_system.py`）
   - 数据驱动：`data/balance/level_curve.json`（Lv1~50，base=120, exponent=1.38）
   - `spend_souls_to_level_up(player, levels)`：逐级扣灵魂碎片，调用 `build._level_up()`
   - 每级获得 1 属性点，由玩家通过 `allocate_attribute` 分配

5. **强化系统**（`systems/upgrade_system.py`）
   - 包装 `weapons/weapon_upgrade.py` 的数值计算，增加成本校验 + 材料扣除
   - 数据驱动：`data/balance/upgrade_cost.json`（+1~+10 费用；4 路线材料）
   - `upgrade_weapon(player, weapon, route)`：扣灵魂碎片 + 材料 → 调用底层强化
   - +1~+5 仅灵魂碎片；+6~+10 加材料；+5 分路线

6. **进度系统**（`systems/quest_system.py`）
   - 追踪 Boss 击杀 / 区域解锁 / 营地激活
   - `record_boss_kill` 自动解锁下一区域
   - `progress_summary()` 返回完整进度字典（供存档使用）

7. **HUD 增强**（`ui/hud.py`）
   - 右下角显示：`◇ {souls}    Lv.{level}`

8. **Player 增强**（`entities/player/player.py`）
   - 新增 `soul_fragments: int = 0` 字段

9. **改造清单**
   - `map/campfire.py`：`try_activate` 接入 `CampfireSystem.activate` + `rest`
   - `map/area.py`：新增 `death_relic` 字段 + 渲染 + reload 时保留遗物
   - `scenes/game_scene.py`：死亡检测 → 自动复活；遗物更新+捡回；灵魂飘字；灵魂碎片入账
   - `player/player_build.py`：新增 `level_up_with_souls()` / `get_soul_cost_to_next()` 委托

10. **冒烟测试** `_test_stage8_core_systems.py` 10 组全部通过；回归测试 `_test_stage8_regression.py` 24 项零破坏

### 1.3.10 第 8.1 阶段补充（死亡 UI + 营地菜单 + 战技补全）

1. **死亡界面**（`ui/death_screen.py`）
   - 全屏黑底渐显 + "你已陨落" 大标题 + 灵魂碎片遗失提示
   - 按 E 从最近营地复活（调用 `RespawnSystem.handle_death`）
   - 按 ESC 回到主菜单
   - `GameScene` 在玩家 HP=0 时先创建遗物 → 显示死亡界面 → 暂停游戏
   - 复活时传送 + 恢复 + 补消耗品 + 敌人重置

2. **营地菜单**（`ui/campfire_menu.py`）
   - F 靠近营地 → 激活 + 打开菜单（暂停游戏）
   - 4 个菜单项：升级 / 武器强化 / 休息 / 离开
   - 升级面板：显示 Lv + 灵魂数 + 成本，按 1~6 分配 6 项属性，按 Enter 消耗灵魂升级
   - 强化面板：显示武器 +N 信息 + 下一级成本，按 Enter 强化
   - W/S 上下选择，Enter 确认，ESC/F 返回

3. **战技补全**（4 个旧武器添加战技）
   - `Sword`：旋风斩（`sword_art.py`）— 360° 大范围击飞
   - `Dagger`：幻影步（`dagger_art.py`）— 闪现至最近敌人身后背刺
   - `Greatsword`：天崩地裂（`greatsword_art.py`）— 超大范围震地强击晕
   - `HolyTome`：神圣之光（`holy_tome_art.py`）— 神圣冲击波 + 自我治疗 25% HP
   - `item_database.py` 中 WeaponItem 的 `weapon_obj` 同步更新（描述也更新）

4. **冒烟测试** `_test_stage8_fixes.py` 三项全部通过

### 1.3.11 第 8.2 阶段修复（武器升级伤害同步 + 营地逻辑 + UI 优化）

1. **武器升级伤害同步修复**（`systems/upgrade_system.py`）
   - 问题：升级后 `stats.atk` 仅通过 `apply_growth()` 更新，缺少 `weapon_item_atk` 增量
   - 修复：若 `player.equipment` 存在，调用 `equipment._sync_stats()` 走完整同步路径

2. **营地交互分离修复**（`map/campfire.py` + `systems/campfire_system.py` + `ui/campfire_menu.py`）
   - 问题：F 键激活营地自动重置怪物（不符合类魂惯例：应选择休息才重置）
   - 修复：`Campfire.try_activate` 仅激活+注册；`CampfireSystem.rest` 不再重置敌人
   - 怪物重置移至 `CampfireMenu._do_rest()`：菜单选择"休息" → 回满 + 补消耗品 + 重置

3. **HUD 提示更新**（`scenes/game_scene.py`）
   - 第二行提示增加 `U: 战技`

4. **灵魂飘字位置修正**（`scenes/game_scene.py`）
   - 问题：击杀怪物后灵魂飘字在玩家头顶（需走到敌人才看到）
   - 修复：`source="enemy"` 的灵魂变化跳过 `_on_soul_fragments_changed`（已在 `_on_enemy_dead` 的敌人死亡位置显示）

5. **升级面板属性描述**（`ui/campfire_menu.py`）
   - 六项属性添加作用描述：力量→重型武器伤害↑…耐性→最大耐力↑负重↑
   - 面板尺寸从 500×440 → 540×520，每行高 52px 容纳双行文字

6. **验证测试** `_test_stage8_fixes2.py` 全部通过

### 1.3.12 第 8.3 阶段修复（死亡界面 + 消耗品验证）

1. **死亡界面不出现修复**（`entities/player/player_combat.py` + `scenes/game_scene.py`）
   - 根因：`PlayerCombat.take_damage` 在 HP=0 时提前将 FSM 切换到 Dead → `GameScene.update` 中 `not self._player.is_dead` 为 False → 死亡界面从不触发
   - 修复：`PlayerCombat.take_damage` 不再切换 Dead（仅发射 `player_death` 事件）；`GameScene.update` 改为 `not self._death_paused` 判断，并自行设置 Dead 状态

2. **消耗品功能验证**（新增 `_test_consumables.py`）
   - 骷髅骨灰等 SpecialItem 的 `use()` 方法正常，通过背包 `use_item` 能正确触发对应事件
   - 毒飞镖发射抛射物、传送石发送事件、Buff 类消耗品均正常
   - 未注册的消耗品 ID（如 `heal_potion_great` 等）确认为 JSON 中未配置，非 bug

### 1.3.13 第 8.4 阶段修复（升级后攻防数值同步）

**根因**：与武器升级问题同源——`Player.allocate_stat()` 和 `PlayerBuild.compute_stats()` 只调用 `stats.apply_growth()`，缺失 `Equipment._sync_stats()` 中的两步：
  - `stats.armor_defense / magic_res_bonus` 设置
  - `stats.atk += weapon_item_atk`（武器物品的基础攻击力）

**修复**（2 处）：
  - `entities/player/player.py` `allocate_stat()`：若 `equipment` 存在 → 走 `equipment._sync_stats()`，否则兜底 `apply_growth()`
  - `player/player_build.py` `compute_stats()`：同上逻辑

**验证**：体魄+2→HP 100→130；力量+2→ATK 包含 weapon_item_atk；防御 23 保持；`atk = growth.get_atk_bonus + weapon_item_atk` 公式正确

### 1.3.14 古墓地图 v3（营地安全区 + 扩大场景）

**变更**：
  - 地图从 80×22 → **100×22**（3200×704 px），增加 20 列空间
  - 3 个营地周围建立 **安全区**（≥5 列无敌人）：
    - cf_01 (col 7):  cols 1-15 安全区，最近敌人 col 20
    - cf_02 (col 56): cols 48-63 安全区，最近敌人 col 45
    - cf_03 (col 92): cols 85-99 安全区，最近敌人 col 82/87
  - 13 名敌人数量不变，位置重新分布保持难度梯度
  - 平台 v2 调整为适配 100 列宽度，所有平台垂直差 3 行 (96px) ≤ 跳跃极限 4 行 (128px)
  - 传送门迁至 col 96

**验证** `_test_map_v3.py`：营地安全区、敌人数量、JSON 格式全部通过

### 1.3.15 第 9 阶段实施摘要（Boss 系统）

1. **数据文件** `data/entities/bosses/duke_rotbone.json`
2. **Boss 基类** + **腐骨公爵** `entities/enemy/bosses/`
3. **雾门** `map/boss_room.py`
4. **Boss 血条** `ui/boss_healthbar.py`
5. **Boss 场景** `scenes/boss_scene.py`
6. **集**成 Area + GameScene
7. **测试** `_test_stage9_boss.py` 11 组通过，回归 24/24

### 1.4 关键设计约定

### 1.4 关键设计约定（后续阶段必须遵守）

- **数据驱动**：所有数值配置必须放 `data/balance/` 或 `data/<category>/` 的 JSON 中
- **组件化**：跨实体复用的逻辑（如击退/韧性/连段）必须独立成 `combat/*` 或 `*_component`
- **状态机**：玩家/敌人/动画统一使用 `utils/state_machine.py` 的 `State` 基类
- **资源加载**：图片/音频统一通过 `utils/resource_cache.py` 加载
- **JSON 加载**：使用 `utils.json_loader.load_from_data_dir(rel_path)`
- **事件总线**：跨模块通信使用 `core.event_manager.event_manager.emit/subscribe`
- **中文注释 + 文档头**：每个模块文件顶部 `# ====` 注释带模块说明
- **命名风格**：snake_case 函数/变量；CapWord 类；常量 UPPER_CASE；私有 `_` 前缀
- **向后兼容**：重构现有模块时保留旧接口（包装/别名）

---

## 二、通用上下文模板（每个新窗口的"开场白"）

> 推荐：在每个新窗口的提示词最前方都加上这段，让 AI 一上来就掌握工程全貌。

```
我正在按 game_rule.md 中的开发顺序推进《烬土传说》——一个 2.5D 横版类魂 RPG，技术栈 Python + Pygame。

工程根目录：d:\Project\MyAIGame
开发文档：d:\Project\MyAIGame\game_rule.md
工作流总览：d:\Project\MyAIGame\DEV_WORKFLOW.md（请先阅读 §1 了解当前进度与设计约定）

【已完成】第 1~7 阶段（工程骨架 / 地图与物理 / 玩家基础 / 战斗核心 / 武器系统 / 物品背包 / 敌人 AI）
- 玩家可移动/跳跃/翻滚/格挡/弹反/三段连击/重击
- 战斗系统：伤害计算、状态异常（流血/中毒/燃烧/冰冻/诅咒/眩晕）、韧性、击退、抛射物物理
- 数据驱动：data/balance/{damage_formula, status_effect_values, loot_tables}.json
- 组件化：KnockbackComponent / PoiseComponent / BlockComponent / ComboWindow / PlayerCombat
- 武器系统全套：sword / dagger / greatsword / holy_tome / spear / axe / bow / staff（8 类）
  - 5 类附魔词条：ElementalEnchant(火/冰/雷/毒) / Lifesteal / Swift / ArmorBreak / StatusBoost
  - 战技系统 WeaponArt（U 键触发，含 mana 消耗 + 冷却）：盾突反击 / 碎盾劈砍 / 穿云箭 / 魔法弹幕
  - 武器强化 +0~+10，5 路线（none/sharp/heavy/blessed/elemental）
  - 数据：data/weapons/{各类武器}_list.json + upgrade_curve.json
- 物品系统全套：item_base / consumable / weapon / armor / item_database / item_manager
  - 7 类消耗品：HealPotion / ManaPotion / StaminaPotion / Antidote / BuffItem / SpecialItem / ArrowItem
  - 套装系统 SetBonusManager（骑士 / 游侠 / 法师 3 套）
  - 物品掉落 / 拾取链路：DroppedItem 落地 + 玩家走入半径自动拾取
  - 数据：data/items/{consumables, armors, upgrade_materials}.json
- 敌人系统全套（7 类全部数据驱动）：
  - infantry / heavy_armor / undead / beast / archer / mage / elite
  - 5 态完整 AI：Idle/Patrol → Alert（警戒值累积）→ Chase → Attack → Return（回归回血）+ Hurt + Dead
  - Archer：远程射 Arrow + 玩家近身后撤；Mage：长吟唱发 MagicBall + 可被打断；Elite：charge_slash + sweep 双技能
  - EnemySpawner：从 data/maps/<area>/enemy_spawns.json 生成，支持 level 缩放
  - LootSystem：data/balance/loot_tables.json 全局掉落表
  - data/entities/enemies/{type}.json 7 个数值文件
- UI 已有：HUD / inventory_screen / equipment_screen / font_manager
- 场景已有：main_menu / game / pause
- 抛射物：physics/projectile.py 含 Projectile / Arrow / MagicBall；GameScene._update_projectiles 每帧推进 + 命中检测

【设计约定】
1. 数据驱动：数值配置必须放 data/ 下 JSON
2. 组件化：跨实体复用逻辑独立成 combat/ 或 *_component 模块
3. 统一使用 utils/state_machine.py 的 State 基类
4. 资源加载用 utils/resource_cache.py
5. JSON 用 utils.json_loader.load_from_data_dir(rel_path)
6. 跨模块通信用 core.event_manager
7. 文件顶部带 # ==== 中文模块说明
8. 重构现有代码必须保留向后兼容接口

【验证流程】每完成一个模块批次后，请通过运行简短的 Python 脚本（SDL_VIDEODRIVER=dummy）做导入与运行时冒烟测试。

【任务】见下方"本次任务"。
```

---

## 三、各阶段任务提示词（按窗口拆分）

每段都是独立的、可直接粘贴的完整提示词。把上面的「通用上下文模板」粘贴在前，再把对应阶段的「本次任务」粘贴在后即可。

---

### 窗口 1 · 第 5 阶段：武器系统补全 ✅ 已完成

> 实施摘要见 §1.3.5。冒烟测试脚本：`_test_stage5_weapons.py`

**本次任务**：完成第 5 阶段——武器系统全套，让玩家可灵活切换 8 类武器并触发各自战技。

**已存在**：`weapons/base_weapon.py`（含 AttackData / WeaponType 常量）、`sword.py / dagger.py / greatsword.py / holy_tome.py`

**需要新建**（按文档顺序）：
1. `weapons/affixes/__init__.py`
2. `weapons/affixes/elemental_enchant.py` —— 元素附魔词条（火/冰/雷/毒）
3. `weapons/affixes/lifesteal.py` —— 吸血词条（5%~10% 伤害转 HP）
4. `weapons/affixes/swift.py` —— 攻速 +10%
5. `weapons/affixes/armor_break.py` —— 无视 15% 防御
6. `weapons/affixes/status_boost.py` —— 状态积累 +20%
7. `weapons/weapon_art.py` —— 战技基类（消耗灵力 + 特效 + 判定）
8. `weapons/types/spear.py` —— 长矛（含格挡反击）
9. `weapons/types/axe.py` —— 战斧（破盾特性）
10. `weapons/types/bow.py` —— 弓（穿云箭，需箭矢消耗）
11. `weapons/types/staff.py` —— 法杖（魔法弹幕战技，调用 `physics.projectile.MagicBall`）
12. `weapons/weapon_upgrade.py` —— 武器强化（+1~+10 + 4 种路线分支）
13. `data/weapons/sword_list.json`、`greatsword_list.json`、`dagger_list.json`、`spear_list.json`、`axe_list.json`、`staff_list.json`、`holy_tome_list.json`、`bow_list.json` —— 各武器数据
14. `weapons/types/__init__.py` 整理导出

**整合要求**：
- 词条系统通过装饰器 / 组合方式挂到 `BaseWeapon` 上，运行时改写 `get_light_attack/get_heavy_attack` 输出
- 战技通过 U 键（`input_handler` 的 `weapon_art` 动作）触发
- 弓必须消耗 `items.consumables.arrow` 计数（如未实现先在物品系统留 TODO）
- 法杖战技调用 `MagicBall` 抛射物
- `weapon_upgrade.py` 的强化数据落到 `data/weapons/upgrade_curve.json`

**验收**：
- 写一个 `_test_stage5_weapons.py`，遍历 8 类武器实例化、调用 `get_light_attack(0/1/2)` 与 `get_heavy_attack()`、附加各词条后伤害变化正确、强化 +1~+10 后基础伤害符合曲线

---

### 窗口 2 · 第 6 阶段：物品与背包系统补全 ✅ 已完成

> 实施摘要见 §1.3.6。冒烟测试脚本：`_test_stage6_items.py`

**本次任务**：完成第 6 阶段——物品分类细化，背包/装备/拾取链路打通。

**已存在**：`items/item_base.py`、`consumable.py`、`weapon.py`、`armor.py`、`item_database.py`；`player/inventory.py`、`equipment.py`

**需要新建**：
1. `items/consumables/__init__.py`
2. `items/consumables/heal_potion.py` —— HP 恢复（草药汤 / 高级圣水）
3. `items/consumables/mana_potion.py` —— 灵力药剂
4. `items/consumables/stamina_potion.py` —— 精力饮剂
5. `items/consumables/antidote.py` —— 万能解药（清状态异常）
6. `items/consumables/buff_items.py` —— 锋刃石粉 / 圣油 / 烈焰松脂 / 铁皮膏 / 狂战药
7. `items/consumables/special_items.py` —— 诅咒解符 / 骷髅骨灰 / 传送石 / 陷阱炸弹 / 毒飞镖
8. `items/consumables/arrow.py` —— 箭矢（弓的弹药，**item_id 必须是 `"arrow"`**，与 `weapons/types/bow.py` 中 `ARROW_ITEM_ID` 对应）
9. `items/equipment/__init__.py`
10. `items/equipment/set_bonus.py` —— 套装效果计算（凑齐 N 件激活）
11. `items/special/__init__.py`
12. `items/special/boss_soul.py` —— 灵核
13. `items/special/upgrade_material.py` —— 强化材料（搭配第 5 阶段 `weapons.weapon_upgrade.WeaponUpgrade` 的 4 路线消耗材料）
14. `items/item_manager.py` —— 物品生成 / 掉落 / 拾取（与 `combat.drop_system` 衔接）
15. `data/items/consumables.json`、`armors.json`、`upgrade_materials.json`

**改造**：
- `entities/player/player_inventory.py`（按文档命名独立模块，包装现有 `player/inventory.py`）
- 现有 `item_database.py` 的注册逻辑改为从 `data/items/*.json` 加载
- **完成 ArrowItem 后**：去掉 `weapons/types/bow.py` 中 `_consume_arrow` / `BowPiercingArrowArt._check_resources` 内 `or True` 的调试兜底，改为严格校验库存

**验收**：
- 玩家在地图上拾取掉落物 → 进背包 → 装备/使用全流程跑通
- 套装效果激活时触发事件 + 飘字提示
- 弓在无箭矢时无法发射、无法触发战技

---

### 窗口 3 · 第 7 阶段：敌人 AI 系统扩展 ✅ 已完成

> 实施摘要见 §1.3.7。冒烟测试脚本：`_test_stage7_enemies.py`

**本次任务**：补齐敌人类型，AI 状态机数据驱动化，敌人生成器接入地图配置。

**已存在**：`base_enemy.py`、`enemy_states.py`、`enemy_stats.py`、`infantry / heavy_armor / undead / beast`

**需要新建**：
1. `data/entities/enemies/infantry.json`、`heavy_armor.json`、`archer.json`、`mage.json`、`elite.json`、`undead.json`、`beast.json` —— 把现有硬编码 `_build_stats` 数据迁移到 JSON
2. `entities/enemy/types/archer.py` —— 弓箭手（远程攻击，使用 `Arrow` 抛射物，近战拉距离 AI）
3. `entities/enemy/types/mage.py` —— 法师（释放 `MagicBall`，含吟唱打断逻辑：吟唱时被打断则进入硬直）
4. `entities/enemy/types/elite.py` —— 精英兵（独特技能 + 强化 AI）
5. `entities/enemy/enemy_ai.py` —— 把 `enemy_states.py` 中的状态拆为：巡逻/警戒/追击/战斗/回归 五态完整闭环
6. `entities/enemy/enemy_spawner.py` —— 读取 `data/maps/<area>/enemy_spawns.json` 生成敌人
7. `data/maps/area_graveyard/enemy_spawns.json` —— 古墓敌人配置（位置 + 类型 + 等级）
8. `data/balance/loot_tables.json` —— 全局掉落表（替换分散在各敌人类的 `drop_table`）
9. `systems/loot_system.py` —— 掉落计算（替换 `combat/drop_system.py` 的简单实现）

**改造**：
- 把所有现有敌人的 `drop_table` / `_build_stats` 移到 JSON
- `area.py` 的敌人创建改为通过 `enemy_spawner.spawn_from_config()`
- `enemy_states.py` 改名/重写为 `enemy_ai.py`（旧文件保留为兼容包装）

**验收**：
- 古墓地图加载时按 JSON 自动生成 5+ 个敌人
- archer 在 200px 外站定射箭，玩家近身则后撤
- mage 吟唱条可被打断
- 精英兵血量明显高于普通兵且释放专属技能

---

### 窗口 4 · 第 8 阶段：游戏规则核心系统 ✅ 已完成

> 实施摘要见 §1.3.9。冒烟测试脚本：`_test_stage8_core_systems.py`，回归测试：`_test_stage8_regression.py`

**本次任务**：实现类魂核心闭环——灵魂碎片掉落/捡回、营地复活、属性升级、武器强化、任务进度。

**前置依赖**：第 5、6、7 阶段已完成（武器/物品/敌人 AI 已就绪）

**需要新建**：
1. `systems/__init__.py`
2. `systems/soul_fragment_system.py` —— 灵魂碎片掉落 / 死亡遗物生成 / 捡回 / 二次死亡永久消失
3. `systems/respawn_system.py` —— 死亡复活（最近营地 + 重置全部敌人 + 重置消耗品）
4. `systems/campfire_system.py` —— 营地系统（已激活营地列表、传送网络、消耗品自动补满）
5. `systems/progression_system.py` —— 升级（消耗灵魂碎片，等级递增曲线，分配六项成长属性）
6. `systems/upgrade_system.py` —— 武器强化（材料消耗 + 等级提升 + +5 路线分支）
7. `systems/quest_system.py` —— 进度（Boss 击杀记录 + 区域解锁状态）
8. `data/balance/level_curve.json` —— 升级所需灵魂碎片曲线
9. `data/balance/upgrade_cost.json` —— 武器强化材料消耗表

**改造**：
- `map/campfire.py` 接入 `campfire_system`（激活时注册到全局 + 触发补满）
- `entities/player/player.py` 死亡事件 → `respawn_system.handle_death()`
- 现有 `player/player_build.py` 重构为 `progression_system` 的薄包装
- 旧 `combat/drop_system.py` 改为只负责生成"灵魂碎片掉落事件"

**验收**：
- 玩家死亡 → 在营地重生 → 原地有遗物 → 捡回 → 灵魂数恢复
- 二次死亡 → 第一次的遗物消失，新遗物生成在新位置
- 营地处可消耗灵魂碎片升级（属性数值实时变化）
- 武器在铁匠（暂用调试键）处可 +1 → 攻击力增加

---

### 窗口 5 · 第 9 阶段：Boss 系统

**本次任务**：实现 5 个 Boss + 完整 Boss 战体验（独立房间 / 两阶段 / 怒气值 / 灵核掉落）。

**前置依赖**：第 8 阶段完成

**需要新建**：
1. `entities/enemy/bosses/__init__.py`
2. `entities/enemy/bosses/base_boss.py` —— Boss 基类（两阶段 / 怒气值 / 硬直抗性 / 专属事件）
3. `entities/enemy/bosses/duke_rotbone.py` —— 腐骨公爵（召唤骷髅 + 毒属性 + 死亡复活）
4. `entities/enemy/bosses/witch_mora.py` —— 沼泽女巫（魔法陷阱 + AOE 火焰）
5. `entities/enemy/bosses/lord_berg.py` —— 锤神伯格（震地攻击 + 破甲机制）
6. `entities/enemy/bosses/assassin_ella.py` —— 幽魂艾拉（隐身闪现 + 幻影分裂）
7. `entities/enemy/bosses/dragon_aegnis.py` —— 堕落龙（三阶段 + 飞行形态）
8. `data/entities/bosses/duke_rotbone.json`、`witch_mora.json`、`lord_berg.json`、`assassin_ella.json`、`dragon_aegnis.json` —— 数值与技能配置
9. `map/boss_room.py` —— Boss 房间（进入触发关门 + Boss 血条 UI 出现）

**整合要求**：
- Boss 进入第二阶段时派发 `boss_phase_change` 事件，UI 血条变色
- Boss 死亡掉落 `BossSoul`（来自第 6 阶段 `items/special/boss_soul.py`）
- 击杀进度写入 `quest_system`，解锁下一区域
- 每个 Boss 至少 3 个独特技能 + 明显前摇动作

**验收**：
- 至少跑通腐骨公爵全流程：进入房间 → 关门 → 一阶段 → 50% 血触发狂化 → 击杀 → 复活 → 二次击杀 → 灵核掉落 → 解锁下一区域

---

### 窗口 6 · 第 10 阶段：NPC 与对话系统

**本次任务**：营地 NPC 可交互，对话树驱动剧情/服务。

**前置依赖**：第 8、9 阶段完成（升级/强化逻辑已就绪）

**需要新建**：
1. `entities/npc/__init__.py`
2. `entities/npc/base_npc.py` —— NPC 基类（交互范围圆 + 对话触发 + 头顶提示符）
3. `entities/npc/keeper.py` —— 营地守护者（升级 / 传送 / 剧情对话）
4. `entities/npc/blacksmith.py` —— 铁匠（武器强化 / 材料购买）
5. `entities/npc/merchant.py` —— 商人（消耗品买卖）
6. `data/dialogues/npc_keeper.json` —— 守护者对话树（含选项分支 + 解锁条件）
7. `data/dialogues/npc_blacksmith.json`
8. `data/dialogues/npc_merchant.json`
9. `data/dialogues/lore_items.json` —— 物品描述/世界观碎片
10. `core/dialogue_engine.py` —— 对话引擎（解析对话树 / 切换节点 / 回调动作）

**改造**：
- `map/area.py` 增加 NPC 列表，区域加载时实例化
- 玩家 F 键交互优先级：营地 > NPC

**验收**：
- 古墓地图营地处放置一个守护者 NPC
- F 键触发对话 → 对话框逐字显示 → 出现选项「升级」「传送」「闲聊」→ 选「升级」打开升级面板
- 铁匠对话可强化武器消耗材料

---

### 窗口 7 · 第 11 阶段：粒子特效与音频

**本次任务**：让战斗有视觉/听觉反馈，区域有专属 BGM。

**需要新建**：
1. `animation/__init__.py`
2. `animation/animation_clip.py` —— 动画片段（帧列表/帧率/循环标志）
3. `animation/sprite_sheet_loader.py` —— 精灵表切割与缓存
4. `animation/animation_state_machine.py` —— 动画状态机（与实体状态机联动）
5. `animation/animator.py` —— 动画控制器
6. `animation/particle_system.py` —— 粒子系统（血溅 / 火焰 / 魔法光效 / 灰尘 / 弹反闪光）
7. `audio/__init__.py`
8. `audio/sfx_player.py` —— 音效播放器（订阅 `HIT_EVENT_TYPE` 等事件）
9. `audio/bgm_player.py` —— 背景音乐播放器（淡入淡出 / 区域切换）
10. `audio/audio_manager.py` —— 音频统一入口
11. `assets/audio/sfx/`（占位空目录）+ `assets/audio/bgm/`（占位）

**接入要求**：
- 命中事件触发血溅粒子 + 打击音
- 弹反成功事件触发金色闪光 + 金属碰撞声
- 状态异常 apply 时触发对应粒子（毒/烧/冰/流血）
- 玩家进入新区域 → BGM 切换淡入淡出
- 暂时使用占位音效（程序生成的方波或纯色矩形粒子），等待资源到位后替换

**验收**：
- 玩家攻击命中敌人 → 红色血溅粒子 + 音效播放
- 进入古墓时播放阴森 BGM
- 弹反成功 → 屏幕短暂金色闪光

---

### 窗口 8 · 第 12 阶段：UI 系统补全

**本次任务**：补齐所有 UI 界面，做到游戏全流程界面闭环。

**已存在**：`ui/font_manager.py`、`hud.py`、`inventory_screen.py`、`equipment_screen.py`

**需要新建**（按文档顺序）：
1. `ui/base_widget.py` —— UI 控件基类（位置/尺寸/事件接口/层级）
2. `ui/damage_number.py` —— 飘字数字（已有 `combat/floating_text.py`，本任务仅做迁移/重命名为标准位置）
3. `ui/notification.py` —— 浮动提示（拾取物品/区域名称/Boss 出现等）
4. `ui/boss_healthbar.py` —— Boss 专属底部双阶段血条
5. `ui/dialogue_box.py` —— NPC 对话框（逐字显示 + 选项分支 + 立绘占位）
6. `ui/status_panel.py` —— 人物属性面板（六项成长属性可视化 + 分配点数）
7. `ui/campfire_menu.py` —— 营地菜单（升级/强化/传送/对话四按钮）
8. `ui/death_screen.py` —— "YOU DIED" 死亡界面（黑屏渐显 + 遗物坐标提示）
9. `ui/loading_screen.py` —— 加载界面（进度条 + 区域背景图占位）
10. `ui/pause_menu_ui.py` —— 暂停菜单（继续/设置/回主菜单）
11. `ui/settings_ui.py` —— 设置界面（音量滑块 + 键位映射 + 分辨率）
12. `ui/main_menu_ui.py` —— 主菜单 UI（开始/继续/设置/退出）

**整合要求**：
- 所有 UI 继承 `BaseWidget`，统一事件分发
- 现有 `inventory_screen.py / equipment_screen.py / hud.py` 迁移为继承 `BaseWidget`
- `damage_number.py` 把 `combat/floating_text.py` 重新挂在 `ui/` 命名空间下（保留兼容导入）
- 设置界面通过 `core.input_handler.remap()` 实时修改键位

**验收**：
- 主菜单 → 开始游戏 → 古墓地图 → 受伤掉血 → 暴击飘字 → ESC 暂停 → 死亡黑屏 → 复活
- Boss 出现时 Boss 血条出现在屏幕底部并随血量缩短

---

### 窗口 9 · 第 13 阶段：场景整合

**本次任务**：把所有功能场景串联，让游戏全流程可玩。

**已存在**：`scenes/main_menu_scene.py`、`game_scene.py`、`pause_scene.py`、`base_scene.py`

**需要新建**：
1. `scenes/loading_scene.py` —— 加载过渡（区域切换时显示）
2. `scenes/boss_scene.py` —— Boss 战专用场景（叠加在 game_scene 之上 / 接管 BGM 与 UI）
3. `scenes/campfire_scene.py` —— 营地交互场景（叠加层 / 暂停 game 逻辑）
4. `scenes/game_over_scene.py` —— 死亡结束场景（YOU DIED + 复活按钮）
5. `scenes/settings_scene.py` —— 设置场景

**改造**：
- 重写 `main_menu_scene.py` 接入 `ui/main_menu_ui.py`
- 改造 `game_scene.py`：进入 Boss 房间触发 push `BossScene`；进入营地触发 push `CampfireScene`
- `pause_scene.py` 接入 `ui/pause_menu_ui.py`
- `core/scene_manager.py` 已支持入栈/出栈，确保营地/暂停场景叠加而不销毁底层 game_scene

**验收**：
- 主菜单 → 加载场景 → 古墓 game_scene → 走到营地 push CampfireScene → 升级 → pop 回 game_scene → 走到 Boss 房间 → push BossScene → 击败 Boss → 加载下一区域

---

### 窗口 10 · 第 14 阶段：存档系统

**本次任务**：实现多槽位存档/读档。

**需要新建**：
1. `save/__init__.py`
2. `save/save_data.py` —— 存档数据结构（玩家状态 / 灵魂数 / 装备 / 背包 / Boss 击杀记录 / 区域解锁 / 营地激活）
3. `save/save_manager.py` —— 序列化（JSON 或 pickle）/反序列化 / 三槽位管理 / 自动备份
4. `save/slots/` 目录占位（`.gitkeep`）

**整合**：
- 营地处自动存档（事件 `campfire_activated`）
- 主菜单"继续游戏"按钮列出三槽位 + 时间/进度信息
- 设置界面提供"删除存档"

**验收**：
- 玩家激活营地 → 自动存档 → 退出游戏 → 继续游戏 → 状态完整恢复（HP/灵魂/装备/Boss 击杀）

---

### 窗口 11 · 第 15 阶段：剩余地图内容

**本次任务**：补齐 5 个区域的地图数据（关卡设计 + 敌人配置）。

**已存在**：`data/maps/area_graveyard/`

**需要新建**：
- `data/maps/area_swamp/tilemap.json` + `enemy_spawns.json` —— 毒沼泽（沼泽女巫 Boss）
- `data/maps/area_ironmine/tilemap.json` + `enemy_spawns.json` —— 铁山矿场（锤神伯格 Boss）
- `data/maps/area_darkforest/tilemap.json` + `enemy_spawns.json` —— 黑暗森林（幽魂艾拉 Boss）
- `data/maps/area_castle/tilemap.json` + `enemy_spawns.json` —— 堕落王城（堕落龙 Boss）
- `assets/tilesets/` 各区域瓦片素材（占位 PNG 即可）
- 更新 `data/maps/world_config.json`：5 区域树状解锁关系

**地图设计要求**：
- 每张地图至少：1 个出生点 + 2 个营地 + 1 个 Boss 房间 + 3 个隐藏区域 + 5 类陷阱
- 体现 2.5D 纵深感（前景遮挡 + 多层平台）
- 区域之间通过 `transition_gate` 连接

**验收**：
- 五张地图均可加载、玩家能从一个区域走到下一个区域、各区域 Boss 击败后解锁路径

---

### 窗口 12 · 第 16 阶段：数值平衡 + 单元测试

**本次任务**：跑全流程平衡 + 完整测试覆盖。

**需要新建**：
1. `tests/__init__.py`
2. `tests/test_damage_calculator.py` —— 伤害公式各分支（防御/元素/弱点/格挡）
3. `tests/test_status_effects.py` —— 各状态异常 apply/remove/update
4. `tests/test_ai_state_machine.py` —— 敌人 AI 巡逻→警戒→追击→战斗→回归闭环
5. `tests/test_collision.py` —— 碰撞检测/单向平台/下穿
6. `tests/test_save_load.py` —— 存档读写 + 数据完整性
7. `tests/test_combat_system.py` —— 战斗集成（玩家攻击→敌人扣血→死亡→掉落）
8. `tests/test_combo_window.py` —— 连段窗口判定
9. `tests/test_parry_system.py` —— 弹反窗口检测
10. `tests/test_projectile.py` —— 抛射物物理 + 命中
11. `tests/test_progression.py` —— 升级曲线 + 武器强化
12. `pytest.ini` —— pytest 配置（禁用警告 + dummy SDL）

**调优要求**：
- 反复修改 `data/balance/*.json`，记录每次调整理由到 `data/balance/CHANGELOG.md`
- 录制全流程通关时长，目标：8~12 小时
- 各 Boss 平均击杀尝试次数：5~15 次
- 玩家从 0 级升到 50 级所需灵魂碎片符合曲线

**验收**：
- `pytest tests/` 全部通过
- 全流程从主菜单到击败堕落龙可一周目通关无 Bug 中断

---

## 四、跨窗口注意事项

### 4.1 工作前必做
1. 阅读 `DEV_WORKFLOW.md` §1（了解当前进度）
2. 用 `git status` 或 `dir` 确认目标文件是否已存在（避免覆盖他人窗口的改动）
3. 阅读 `game_rule.md` 中对应阶段的设计要求

### 4.2 工作完成后必做
1. 在工程根目录创建 `_test_stage<N>_<feature>.py` 冒烟测试脚本
2. 用 `python _test_stage<N>_xxx.py` 验证可运行
3. 在 `DEV_WORKFLOW.md` §1.1 表格中将对应阶段标记为 ✅
4. （可选）把临时测试脚本移动到 `tests/` 转为正式测试
5. 同步更新`二、通用上下文模板（每个新窗口的"开场白"）`

### 4.3 容易踩的坑
- **循环导入**：`combat/` 与 `entities/` 互相引用时使用 `TYPE_CHECKING`
- **Pygame 初始化**：测试脚本必须先 `pygame.init()` 才能创建 `Rect` 之外的对象
- **数据驱动**：新增数值前先看 `data/balance/` 是否已有对应 JSON
- **事件总线**：场景退出时记得 `event_manager.unsubscribe()` 防止悬空引用
- **状态机**：注册新状态后必须确保至少有一个 `change_state` 路径可达，否则永远进不去
- **向后兼容**：重构现有模块务必保留旧导入路径（用 re-export 或包装类）

### 4.4 推荐工作顺序
窗口 1（武器）✅ 已完成

窗口 2（物品）与窗口 3（敌人 AI）可**并行**推进（无强依赖）

窗口 4（规则系统）依赖 1、2、3 完成

窗口 5（Boss）依赖 4

窗口 6（NPC）依赖 4

窗口 7（特效音频）可与 6 并行

窗口 8（UI）依赖 4、5、6（需要 Boss 血条 / 营地菜单）

窗口 9（场景串联）依赖 8

窗口 10（存档）依赖 9

窗口 11（地图内容）可在 1~10 任意时间并行制作

窗口 12（测试）放最后

---

## 五、提示词使用示范

打开新窗口后的标准开场（以"窗口 1 · 武器系统"为例）：

```
我正在按 game_rule.md 中的开发顺序推进《烬土传说》——一个 2.5D 横版类魂 RPG，技术栈 Python + Pygame。

工程根目录：d:\Project\MyAIGame
开发文档：d:\Project\MyAIGame\game_rule.md
工作流总览：d:\Project\MyAIGame\DEV_WORKFLOW.md（请先阅读 §1 了解当前进度与设计约定）

【已完成】第 1~4 阶段
[...粘贴 §2 通用上下文模板剩余部分...]

【本次任务】
[...粘贴对应窗口"本次任务"全部内容...]

请按以下流程工作：
1. 先用 list_files_recursive 看 weapons/ 现状
2. 阅读现有 base_weapon.py / sword.py 理解模板
3. 制定增量实现计划，征求我同意后开工
4. 完成后写冒烟测试 _test_stage5_weapons.py 并运行验证
5. 在 DEV_WORKFLOW.md §1.1 中将第 5 阶段标记为 ✅
```

> 把这套模板放在你的剪贴板管理器里，每次开新窗口三秒钟即可启动。



