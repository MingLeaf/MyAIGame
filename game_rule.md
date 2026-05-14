# 《烬土传说》—— 2.5D 中古魔幻类魂 RPG 游戏设计文案

---

## 一、游戏概述

**游戏类型**：2.5D 横版 / 斜视角类魂动作 RPG
**世界观**：中古魔幻冒险世界——"烬土大陆"，曾经繁荣的王国因神秘诅咒陷入混乱，各地领主割据为王，腐化堕落。玩家扮演一名流浪英雄，踏上征途，逐一击败各路领主，揭开大陆灭亡的真相。

**核心体验**：
- 高难度、重操作的战斗体验
- 死亡惩罚与资源管理
- 探索驱动的地图设计
- 装备与属性构建的 Build 乐趣

---

## 二、玩家（Player）属性系统

### 2.1 基础属性

| 属性名 | 说明 | 备注 |
|---|---|---|
| **生命值（HP）** | 玩家当前存活的血量上限 | 归零则死亡 |
| **耐力值（Stamina）** | 用于翻滚、格挡、攻击的消耗资源 | 停止动作后自动回复 |
| **灵力值（Mana）** | 施放魔法/特殊技能的消耗资源 | 通过消耗品或特定行为恢复 |
| **负重（Equip Load）** | 当前装备总重量 / 最大负重 | 影响翻滚距离和速度 |
| **韧性（Poise）** | 抗硬直能力，超过阈值才会被打断动作 | 重甲提供更高韧性 |

### 2.2 成长属性（可通过升级分配点数）

| 属性名 | 主要效果 |
|---|---|
| **力量（Strength）** | 提升重型武器伤害，满足重武器装备要求 |
| **敏捷（Dexterity）** | 提升轻型/速度型武器伤害，提升翻滚距离 |
| **智慧（Intelligence）** | 提升魔法伤害、魔法类消耗品效果 |
| **信仰（Faith）** | 提升神圣类技能、治疗类消耗品效果 |
| **体魄（Vitality）** | 提升最大 HP 与耐力恢复速度 |
| **耐性（Endurance）** | 提升最大 Stamina 与最大负重 |

### 2.3 衍生属性

| 衍生属性 | 计算方式 |
|---|---|
| 物理攻击力 | 武器基础攻击 + 力量/敏捷加成 |
| 魔法攻击力 | 武器/法器基础 + 智慧加成 |
| 物理防御力 | 护甲合计防御值 |
| 魔法抗性 | 护甲魔法抗性合计 |
| 翻滚类型 | 负重率 < 30% 快滚 / 30~70% 中滚 / >70% 慢滚 / >100% 无法翻滚 |

---

## 三、战斗系统

### 3.1 基础战斗动作

| 动作 | 消耗 | 说明 |
|---|---|---|
| 轻攻击 | 少量耐力 | 速度快，可连段（最多3连击） |
| 重攻击 | 大量耐力 | 伤害高，可打破敌人格挡，有追加打击效果 |
| 翻滚（闪避） | 中量耐力 | 无敌帧窗口，方向可控 |
| 格挡 | 持续消耗耐力 | 减少受到伤害，耐力归零则格挡破防 |
| 弹反（完美格挡） | 无消耗 | 格挡触发瞬间有极短完美格挡窗口，成功触发弹反，对敌人造成高伤害+硬直 |
| 蓄力攻击 | 大量耐力 | 长按重攻击键，释放时造成范围/穿透攻击 |
| 特殊技能 | 消耗灵力 | 各武器独有的战技（Weapon Art） |

### 3.2 伤害计算

```
最终伤害 = (攻击方攻击力 × 技能倍率) - (防御方防御值 × 防御系数)
```

- **弱点伤害**：攻击命中敌人弱点（背刺、倒地追击）造成 ×1.5 倍伤害
- **元素克制**：火属性克制冰属性敌人（×1.3），神圣克制不死类（×1.5）
- **格挡减伤**：格挡后受到 30%~80% 伤害（取决于盾牌格挡率）

### 3.3 状态异常

| 异常状态 | 触发方式 | 效果 |
|---|---|---|
| 流血（Bleed） | 累积流血值达到阈值 | 瞬间爆发扣除当前HP的15% |
| 中毒（Poison） | 持续受到毒属性攻击 | 持续扣血，持续30秒 |
| 燃烧（Burn） | 火焰攻击 | 持续扣血+降低防御，可以滚地消除 |
| 冰冻（Freeze） | 寒冰攻击 | 硬直2秒，期间受到额外20%伤害 |
| 诅咒（Curse） | 特定boss技能 | 最大HP减半，击杀一定数量敌人解除 |
| 眩晕（Stun） | 韧性被打空 | 短暂硬直，可被处决 |

---

## 四、NPC 与敌人系统

### 4.1 普通敌人（小兵）属性

| 属性 | 说明 |
|---|---|
| **HP** | 生命值 |
| **攻击力** | 物理/魔法攻击 |
| **防御力** | 物理/元素防御 |
| **移动速度** | 巡逻速度 / 追击速度（追击时加快） |
| **视野范围** | 扇形视野，超出范围则失去目标 |
| **追击距离** | 最大追击半径，超出后停止追击并回原位 |
| **警觉值** | 玩家进入视野后开始累积，满了触发追击 |
| **掉落物** | 击败后掉落的物品/金币/经验 |

### 4.2 敌人 AI 行为状态机

```
[巡逻] → 发现玩家（视野+警觉值） → [警戒] → 确认目标 → [追击]
   ↑                                                        ↓
[回归]  ← 超出追击距离 或 失去视野一定时间 ←──────── [战斗]
```

- **巡逻**：沿固定路线或随机游走
- **警戒**：发出警告音效，转向玩家，警觉值快速累积
- **追击**：全速向玩家冲锋，进入攻击范围后转入战斗
- **战斗**：执行攻击 AI（近战、远程、技能循环）
- **回归**：返回出生点，HP 缓慢回复，重置警觉值

### 4.3 敌人类型设计

| 类型 | 代表单位 | 特征 |
|---|---|---|
| **普通步兵** | 亡灵剑士、腐化士兵 | 近战，简单攻击循环，低韧性 |
| **重甲兵** | 石像骑士、铁甲卫兵 | 高防御高韧性，攻击慢但击退力强 |
| **弓箭手** | 腐骨射手、精灵游侠 | 远程攻击，近战脆，优先拉距离 |
| **法师** | 黑袍术士、邪祭司 | 远程魔法，释放大范围法术，可被打断吟唱 |
| **精英兵** | 古代骑士、堕落圣骑士 | mini-boss 级，独特技能，强AI |
| **不死类** | 骷髅战士 | 击倒后会复活，需圣属性或骨灰消灭 |
| **野兽类** | 荒原狼、巨型熊怪 | 高移速，连续撕咬，易触发流血 |

---

## 五、Boss 系统

### 5.1 Boss 通用设计规则

- 每个 Boss 拥有**独立 Boss 房间**，进入后门关闭
- Boss 拥有**两阶段**：HP 降至 50% 时进入狂化阶段，速度加快，新增技能
- 击败 Boss 后获得：**固定奖励（Boss 专属物品 + 大量升级货币）+ 解锁新区域**
- Boss 死亡掉落**灵核（Boss Soul）**，可兑换专属武器或直接转化为升级货币

### 5.2 Boss 属性示例

| 属性 | 说明 |
|---|---|
| **生命值（HP）** | 远高于普通敌人 |
| **阶段切换阈值** | 默认 50% HP |
| **弱点** | 特定部位/元素 |
| **抗性** | 免疫或减伤的元素/状态 |
| **怒气值（Fury）** | 积累后释放超级技能 |
| **硬直抗性** | 极高，需累积伤害才可触发踉跄/倒地 |

### 5.3 Boss 示例列表

| Boss 名 | 属性特点 | 弱点 | 抗性 | 特色机制 |
|---|---|---|---|---|
| **墓地领主·腐骨公爵** | 召唤骷髅兵，毒属性 | 圣属性 | 毒免疫 | 死亡复活一次，需二次击杀 |
| **沼泽女巫·莫拉** | 远程魔法，AOE 火焰 | 冰属性 | 火免疫 | 会设置魔法陷阱，需要清除陷阱 |
| **铁山领主·锤神伯格** | 全身重甲，震地攻击 | 雷电、流血 | 物理减伤50% | 盔甲可被破坏，破甲后弱点暴露 |
| **暗影刺客·幽魂艾拉** | 高速连击，隐身闪现 | 神圣、火 | 流血免疫 | 会分裂出幻影，需辨认真身 |
| **堕落龙·艾格尼斯** | 终章Boss，飞龙形态 | 冰、圣 | 火焰免疫 | 多阶段（3阶段），二阶段飞行加入 |

---

## 六、武器系统

### 6.1 武器分类

| 类别 | 代表武器 | 主要属性依赖 | 特点 |
|---|---|---|---|
| **单手剑** | 骑士剑、细剑 | 力量/敏捷 | 均衡速度与伤害，可配盾 |
| **大剑** | 巨剑、圣战重剑 | 力量 | 高伤害大范围，速度慢，双手持用 |
| **匕首** | 毒刃、暗影刀 | 敏捷 | 极速连击，高暴击，易触发状态异常 |
| **长矛** | 骑士枪、龙牙枪 | 敏捷/力量 | 攻击距离长，可格挡同时反击 |
| **战斧** | 铁斧、古代战斧 | 力量 | 高打击感，强力击破格挡 |
| **法杖** | 魔法导杖、黑曜杖 | 智慧 | 远程魔法输出，需灵力 |
| **圣典** | 神圣典籍 | 信仰 | 治疗+神圣伤害，对不死强效 |
| **弓** | 猎人短弓、战术长弓 | 敏捷 | 远程物理，需箭矢消耗品 |

### 6.2 武器词条系统

每把武器除基础属性外，可拥有 1~3 个词条：

- **元素附魔**：附加火/冰/雷/毒伤害
- **吸血**：造成伤害的5%~10% 转化为 HP
- **迅捷**：攻击速度提升 10%
- **破甲**：无视敌人15% 防御
- **状态强化**：对应状态异常积累速度+20%

### 6.3 武器战技（Weapon Art）

每类武器拥有独特战技，消耗灵力使用：

| 武器 | 战技名 | 效果 |
|---|---|---|
| 单手剑 | 旋风斩 | 360度旋转斩击，打飞周围敌人 |
| 大剑 | 天崩地裂 | 跳起重劈，巨大范围震地，强力击晕 |
| 匕首 | 幻影步 | 瞬间闪至身后，背刺爆伤 |
| 法杖 | 魔法弹幕 | 发射6枚追踪魔法弹 |
| 弓 | 穿云箭 | 充能射出穿透全屏的箭矢 |

---

## 七、消耗品系统

### 7.1 消耗品分类

**恢复类**

| 物品 | 效果 | 携带上限 |
|---|---|---|
| 草药汤 | 恢复 30% HP | 5 个 |
| 高级圣水 | 立即恢复全部 HP | 2 个 |
| 灵力药剂 | 恢复 50% Mana | 3 个 |
| 精力饮剂 | 立即恢复全部 Stamina | 3 个 |
| 万能解药 | 清除所有负面状态 | 3 个 |

> 💡 **篝火补充机制**：类魂设计，到达营地/篝火点后所有消耗品（限定类）自动补充至上限，同时复活所有已死亡敌人

**强化类**

| 物品 | 效果 | 持续时间 |
|---|---|---|
| 锋刃石粉 | 武器附加物理伤害+15% | 60秒 |
| 圣油 | 武器附加神圣属性 | 60秒 |
| 烈焰松脂 | 武器附加火焰属性 | 60秒 |
| 铁皮膏 | 物理防御+20% | 90秒 |
| 狂战药 | 攻击力+20%，防御-10% | 45秒 |

**特殊类**

| 物品 | 效果 |
|---|---|
| 诅咒解符 | 解除诅咒状态 |
| 骷髅骨灰 | 永久消灭复活中的骷髅 |
| 传送石 | 立即传送到最近营地 |
| 陷阱炸弹 | 放置一个可引爆的炸弹陷阱 |
| 毒飞镖 | 远程投掷，触发中毒状态 |

---

## 八、地图与关卡设计

### 8.1 地图结构

整个大陆地图由多个**区域**组成，呈现树状解锁结构：

```
[起始地——荒野村庄]
       ↓
  [古墓地带] → Boss①：腐骨公爵
       ↓
  [毒沼泽地] → Boss②：沼泽女巫
       ↓
  [铁山矿场] → Boss③：锤神伯格
       ↓
  [黑暗森林] → Boss④：幽魂艾拉
       ↓
  [堕落王城] → 终章Boss：堕落龙
```

### 8.2 营地（篝火点）系统

- 每个区域设置 1~3 个营地
- 营地功能：**补充消耗品 / 升级角色 / 传送至其他营地 / NPC 对话**
- 死亡后在上一个激活的营地复活，掉落遗物（携带的升级货币），可重新捡回

### 8.3 2.5D 地图特色

- 地图具有**纵深感**，画面为斜视角，可进入建筑内部
- 部分路段有**前景遮挡**，制造隐藏路径和隐秘区域
- 存在**纵向跳跃**，可以跳上/跳下不同高度的平台
- **陷阱机关**：刺墙、坠石、燃烧地面等环境危险

---

## 九、升级与成长系统

### 9.1 升级货币——"灵魂碎片"

- 击败敌人、开启宝箱获取
- 死亡后原地掉落，可在不死亡的情况下原地捡回，若再次死亡则永久消失
- 在营地 NPC 处消耗灵魂碎片升级，每次升级所需量递增

### 9.2 武器升级

- 通过收集**强化材料**（各区域特产）在铁匠处强化
- 强化等级：+1 ~ +10，每级提升基础攻击力
- +5 后可选择武器强化路线（力量型 / 敏捷型 / 魔法型 / 状态型）

### 9.3 护甲系统

- 护甲分：头盔、胸甲、护手、腿甲，每件独立穿戴
- 护甲影响：防御力 / 负重 / 特殊效果（如某套装增加特定战技效果）
- 套装效果：凑齐同套护甲后激活套装特效

---

## 十、游戏进程与核心循环

```
探索地图
   ↓
击败小兵、获取灵魂碎片和物品
   ↓
发现营地 → 升级/强化/补充消耗品
   ↓
挑战精英怪和领主Boss
   ↓
击败Boss → 解锁新区域 + 获取强力道具
   ↓
重复上述循环，直至击败最终Boss
```

**死亡机制**：
- 死亡 → 在上一营地复活 → 灵魂碎片留在死亡点 → 敌人全部复活
- 死亡惩罚合理，鼓励玩家提升技术而非惩罚过于严苛

---

## 十一、设计原则总结

| 原则 | 说明 |
|---|---|
| **难度公正** | 死亡总有规律可循，不存在随机一刀秒杀 |
| **Build 多样性** | 力量、敏捷、魔法、信仰各有强力流派 |
| **探索奖励** | 隐藏区域、隐藏宝箱提供强力奖励，鼓励探索 |
| **Boss 记忆** | Boss 技能有明显的动作前摇，鼓励玩家背板学习 |
| **叙事留白** | 通过物品描述、NPC 只言片语构建世界观，而非强制剧情 |

---

# 《烬土传说》Python 工程目录结构设计

> 基于 **Pygame** 库（无引擎纯 Python 开发）进行设计，采用 **数据驱动 + 组件化** 架构思想

---

```
MyAIGame/                                    # 项目根目录
│
├── main.py                                  # 程序入口，初始化游戏并启动主循环
├── requirements.txt                         # Python 依赖库清单（pygame 等）
├── config.py                                # 全局常量配置（分辨率、帧率、版本号等）
│
├── core/                                    # 核心引擎层（游戏底层驱动）
│   ├── __init__.py
│   ├── game.py                              # 游戏主类，管理主循环、场景切换、全局状态
│   ├── scene_manager.py                     # 场景管理器，负责场景的入栈/出栈/切换
│   ├── event_manager.py                     # 全局事件总线，解耦各模块间通信
│   ├── clock.py                             # 游戏时钟，管理 delta_time、帧率控制
│   ├── camera.py                            # 摄像机系统，跟随玩家、视口裁剪、震动效果
│   ├── input_handler.py                     # 输入管理器，统一处理键盘/手柄/鼠标输入
│   └── renderer.py                          # 渲染器，管理分层绘制顺序（背景/实体/UI）
│
├── scenes/                                  # 场景层（各功能界面和游戏关卡）
│   ├── __init__.py
│   ├── base_scene.py                        # 场景基类，定义 update/render/handle_event 接口
│   ├── main_menu_scene.py                   # 主菜单场景（开始游戏/继续/设置/退出）
│   ├── game_scene.py                        # 核心游戏场景，驱动地图、实体、战斗的主逻辑
│   ├── boss_scene.py                        # Boss 战斗专用场景（关闭大门、Boss 血条 UI）
│   ├── campfire_scene.py                    # 营地交互场景（升级/强化/传送/NPC 对话）
│   ├── pause_scene.py                       # 暂停菜单场景（叠加在游戏场景上层）
│   ├── game_over_scene.py                   # 死亡/游戏结束场景（显示遗物、复活提示）
│   ├── loading_scene.py                     # 区域加载过渡场景
│   └── settings_scene.py                    # 设置场景（音量/键位/画面）
│
├── entities/                                # 实体层（游戏世界中所有对象）
│   ├── __init__.py
│   ├── base_entity.py                       # 实体基类，包含位置、碰撞箱、生命周期管理
│   │
│   ├── player/                              # 玩家模块
│   │   ├── __init__.py
│   │   ├── player.py                        # 玩家主类，整合所有玩家子系统
│   │   ├── player_stats.py                  # 玩家属性（HP/Stamina/Mana/力量/敏捷等）
│   │   ├── player_controller.py             # 玩家输入控制器（移动/攻击/翻滚/格挡）
│   │   ├── player_combat.py                 # 玩家战斗逻辑（攻击判定、弹反、处决）
│   │   ├── player_inventory.py              # 玩家背包（武器/护甲/消耗品持有管理）
│   │   └── player_state_machine.py          # 玩家状态机（Idle/Run/Attack/Roll/Dead 等）
│   │
│   ├── enemies/                             # 敌人模块
│   │   ├── __init__.py
│   │   ├── base_enemy.py                    # 敌人基类，包含通用属性和 AI 状态机框架
│   │   ├── enemy_ai.py                      # 敌人 AI 核心（巡逻/警戒/追击/战斗/回归）
│   │   ├── enemy_stats.py                   # 敌人属性数据类（HP/攻击/视野/追击距离等）
│   │   ├── enemy_spawner.py                 # 敌人生成器，根据地图数据动态生成敌人
│   │   │
│   │   ├── types/                           # 各类型敌人具体实现
│   │   │   ├── infantry.py                  # 普通步兵（亡灵剑士/腐化士兵）
│   │   │   ├── heavy_armor.py               # 重甲兵（石像骑士/铁甲卫兵）
│   │   │   ├── archer.py                    # 弓箭手（腐骨射手/精灵游侠）
│   │   │   ├── mage.py                      # 法师（黑袍术士/邪祭司），含吟唱打断逻辑
│   │   │   ├── elite.py                     # 精英兵，拥有独特技能的 mini-boss 级敌人
│   │   │   ├── undead.py                    # 不死类（骷髅），含复活逻辑
│   │   │   └── beast.py                     # 野兽类（荒原狼/巨型熊怪），高速连击
│   │   │
│   │   └── bosses/                          # Boss 具体实现
│   │       ├── base_boss.py                 # Boss 基类（两阶段机制/怒气值/专属血条）
│   │       ├── duke_rotbone.py              # Boss①：腐骨公爵（召唤骷髅/毒属性/死亡复活）
│   │       ├── witch_mora.py                # Boss②：沼泽女巫（魔法陷阱/火焰AOE）
│   │       ├── lord_berg.py                 # Boss③：锤神伯格（震地攻击/破甲机制）
│   │       ├── assassin_ella.py             # Boss④：幽魂艾拉（隐身闪现/幻影分裂）
│   │       └── dragon_aegnis.py             # 终章Boss：堕落龙（三阶段/飞行形态）
│   │
│   └── npc/                                 # 非战斗 NPC
│       ├── __init__.py
│       ├── base_npc.py                      # NPC 基类（对话触发、交互范围）
│       ├── blacksmith.py                    # 铁匠（武器强化/材料购买）
│       ├── merchant.py                      # 商人（消耗品购买/出售）
│       └── keeper.py                        # 营地守护者（升级/传送/剧情对话）
│
├── combat/                                  # 战斗系统层（独立于实体的战斗逻辑）
│   ├── __init__.py
│   ├── damage_calculator.py                 # 伤害计算器（攻击力/防御/技能倍率/克制）
│   ├── hitbox.py                            # 攻击判定框，管理攻击区域的生命周期
│   ├── status_effects.py                    # 状态异常系统（流血/中毒/燃烧/冰冻/诅咒）
│   ├── status_effect_manager.py             # 状态异常管理器，挂载/更新/移除角色身上的异常
│   ├── combo_system.py                      # 连段系统，管理轻/重攻击的连击窗口和衔接
│   ├── parry_system.py                      # 弹反系统（完美格挡窗口检测与弹反触发）
│   ├── knockback.py                         # 击退/击飞物理计算
│   └── poise_system.py                      # 韧性系统（韧性值累积/清空/触发硬直）
│
├── weapons/                                 # 武器系统层
│   ├── __init__.py
│   ├── base_weapon.py                       # 武器基类（基础攻击力/属性依赖/词条/战技）
│   ├── weapon_art.py                        # 战技系统基类（消耗灵力/特效/判定）
│   ├── weapon_upgrade.py                    # 武器强化系统（+1~+10/路线选择）
│   │
│   ├── types/                               # 各武器类型实现
│   │   ├── sword.py                         # 单手剑（旋风斩战技）
│   │   ├── greatsword.py                    # 大剑（天崩地裂战技）
│   │   ├── dagger.py                        # 匕首（幻影步战技/流血积累）
│   │   ├── spear.py                         # 长矛（格挡反击机制）
│   │   ├── axe.py                           # 战斧（破盾特性）
│   │   ├── staff.py                         # 法杖（魔法弹幕战技）
│   │   ├── holy_tome.py                     # 圣典（治疗+神圣伤害）
│   │   └── bow.py                           # 弓（穿云箭/需箭矢消耗品）
│   │
│   └── affixes/                             # 武器词条模块
│       ├── __init__.py
│       ├── elemental_enchant.py             # 元素附魔词条（火/冰/雷/毒）
│       ├── lifesteal.py                     # 吸血词条
│       ├── swift.py                         # 迅捷词条
│       ├── armor_break.py                   # 破甲词条
│       └── status_boost.py                  # 状态强化词条
│
├── items/                                   # 物品系统层
│   ├── __init__.py
│   ├── base_item.py                         # 物品基类（名称/描述/图标/使用逻辑）
│   ├── item_manager.py                      # 物品管理器（生成/掉落/拾取）
│   │
│   ├── consumables/                         # 消耗品实现
│   │   ├── __init__.py
│   │   ├── heal_potion.py                   # 草药汤/高级圣水（HP 恢复）
│   │   ├── mana_potion.py                   # 灵力药剂（Mana 恢复）
│   │   ├── stamina_potion.py                # 精力饮剂（Stamina 恢复）
│   │   ├── antidote.py                      # 万能解药（清除负面状态）
│   │   ├── buff_items.py                    # 强化类消耗品（锋刃石粉/烈焰松脂/铁皮膏等）
│   │   ├── special_items.py                 # 特殊消耗品（骨灰/传送石/陷阱炸弹/毒飞镖）
│   │   └── arrow.py                         # 箭矢（弓的专用弹药消耗品）
│   │
│   ├── equipment/                           # 装备物品（数据定义，逻辑在 weapons/ 内）
│   │   ├── __init__.py
│   │   ├── armor.py                         # 护甲物品类（头/胸/手/腿四部位数据）
│   │   └── set_bonus.py                     # 套装效果计算
│   │
│   └── special/                             # 特殊功能物品
│       ├── boss_soul.py                     # 灵核（击败 Boss 掉落，可兑换或转化货币）
│       └── upgrade_material.py              # 强化材料（各区域特产材料数据）
│
├── map/                                     # 地图系统层
│   ├── __init__.py
│   ├── world_map.py                         # 世界地图管理，区域解锁状态、区域跳转
│   ├── area.py                              # 单个区域类（含瓦片地图/实体列表/营地位置）
│   ├── tile_map.py                          # 瓦片地图渲染（2.5D 斜视角层次渲染）
│   ├── tile.py                              # 单个瓦片类（类型/碰撞/前景遮挡/特效）
│   ├── layer_renderer.py                    # 分层渲染器（背景层/地面层/实体层/前景遮挡层）
│   ├── collision_map.py                     # 碰撞地图（静态碰撞检测，墙壁/平台/悬崖）
│   ├── platform.py                          # 平台对象（单向跳跃平台逻辑）
│   ├── trap.py                              # 环境陷阱（刺墙/坠石/燃烧地面）
│   ├── campfire.py                          # 营地篝火对象（激活/传送/补充消耗品）
│   └── transition_gate.py                   # 区域传送门/入口（触发区域切换）
│
├── physics/                                 # 物理系统层（轻量级，不依赖引擎）
│   ├── __init__.py
│   ├── collision_detector.py                # 碰撞检测（AABB 矩形碰撞/圆形碰撞）
│   ├── gravity.py                           # 重力系统（控制跳跃和坠落）
│   ├── movement_resolver.py                 # 移动解算器（位移+碰撞响应合并处理）
│   └── projectile.py                        # 抛射物物理（箭矢/魔法弹的轨迹计算）
│
├── ui/                                      # UI 系统层
│   ├── __init__.py
│   ├── base_widget.py                       # UI 控件基类（位置/尺寸/渲染/事件接口）
│   ├── hud.py                               # 游戏内 HUD（HP条/Stamina条/Mana条/负重）
│   ├── boss_healthbar.py                    # Boss 专属血条（底部大型双阶段血条）
│   ├── inventory_panel.py                   # 背包界面（武器/护甲/消耗品格子）
│   ├── equipment_panel.py                   # 装备栏界面（6个装备槽+属性预览）
│   ├── status_panel.py                      # 人物属性界面（查看/分配升级点数）
│   ├── campfire_menu.py                     # 营地菜单 UI（升级/强化/传送/NPC对话）
│   ├── dialogue_box.py                      # NPC 对话框（逐字显示/选项分支）
│   ├── notification.py                      # 浮动提示（拾取物品/状态异常/区域提示）
│   ├── damage_number.py                     # 飘字伤害数字（普通/暴击/治疗颜色区分）
│   ├── main_menu_ui.py                      # 主菜单 UI
│   ├── pause_menu_ui.py                     # 暂停菜单 UI
│   ├── settings_ui.py                       # 设置界面 UI（音量滑块/键位映射）
│   ├── death_screen.py                      # 死亡界面（YOU DIED 效果/遗物提示）
│   ├── loading_screen.py                    # 加载界面（进度条/区域背景图）
│   └── font_manager.py                      # 字体管理器（中英文字体加载与缓存）
│
├── animation/                               # 动画系统层
│   ├── __init__.py
│   ├── animator.py                          # 动画控制器（播放/切换/混合动画状态）
│   ├── animation_clip.py                    # 动画片段（帧列表/帧率/是否循环）
│   ├── sprite_sheet_loader.py               # 精灵表加载器（切割帧/缓存管理）
│   ├── animation_state_machine.py           # 动画状态机（与实体状态机联动）
│   └── particle_system.py                   # 粒子特效系统（血溅/火焰/魔法光效/灰尘）
│
├── audio/                                   # 音频系统层
│   ├── __init__.py
│   ├── audio_manager.py                     # 音频管理器（统一控制BGM和音效的播放）
│   ├── bgm_player.py                        # 背景音乐播放器（循环/淡入淡出/区域切换）
│   └── sfx_player.py                        # 音效播放器（攻击/受伤/环境音效触发）
│
├── systems/                                 # 游戏规则系统层（跨模块的业务逻辑）
│   ├── __init__.py
│   ├── progression_system.py                # 升级成长系统（经验/灵魂碎片/属性点分配）
│   ├── soul_fragment_system.py              # 灵魂碎片系统（掉落/遗物生成/捡回/消失）
│   ├── respawn_system.py                    # 死亡复活系统（营地复活/敌人重置）
│   ├── campfire_system.py                   # 营地系统（消耗品补充/传送网络管理）
│   ├── upgrade_system.py                    # 武器强化系统（材料消耗/等级提升/路线分支）
│   ├── loot_system.py                       # 掉落系统（掉落表配置/随机掉落逻辑）
│   └── quest_system.py                      # 任务/进度系统（Boss击杀进度/区域解锁记录）
│
├── data/                                    # 数据配置层（数据驱动，与代码解耦）
│   ├── entities/                            # 实体数据
│   │   ├── player_base_stats.json           # 玩家初始属性基准值
│   │   ├── enemies/                         # 各类敌人的属性数据文件
│   │   │   ├── infantry.json
│   │   │   ├── heavy_armor.json
│   │   │   ├── archer.json
│   │   │   ├── mage.json
│   │   │   ├── elite.json
│   │   │   ├── undead.json
│   │   │   └── beast.json
│   │   └── bosses/                          # 各 Boss 属性与技能数据
│   │       ├── duke_rotbone.json
│   │       ├── witch_mora.json
│   │       ├── lord_berg.json
│   │       ├── assassin_ella.json
│   │       └── dragon_aegnis.json
│   │
│   ├── weapons/                             # 武器数据
│   │   ├── sword_list.json                  # 单手剑列表（名称/基础攻击/词条/战技）
│   │   ├── greatsword_list.json
│   │   ├── dagger_list.json
│   │   ├── spear_list.json
│   │   ├── axe_list.json
│   │   ├── staff_list.json
│   │   ├── holy_tome_list.json
│   │   └── bow_list.json
│   │
│   ├── items/                               # 物品数据
│   │   ├── consumables.json                 # 所有消耗品的属性/效果/携带上限
│   │   ├── armors.json                      # 所有护甲的属性/负重/套装归属
│   │   └── upgrade_materials.json           # 强化材料来源与用途
│   │
│   ├── maps/                                # 地图数据
│   │   ├── world_config.json                # 世界地图总配置（区域列表/解锁条件）
│   │   ├── area_graveyard/                  # 古墓地带区域数据
│   │   │   ├── tilemap.json                 # 瓦片地图数据（Tiled 格式兼容）
│   │   │   └── enemy_spawns.json            # 该区域敌人生成点配置
│   │   ├── area_swamp/                      # 毒沼泽地区域数据
│   │   ├── area_ironmine/                   # 铁山矿场区域数据
│   │   ├── area_darkforest/                 # 黑暗森林区域数据
│   │   └── area_castle/                     # 堕落王城区域数据
│   │
│   ├── dialogues/                           # 对话/剧情数据
│   │   ├── npc_keeper.json                  # 营地守护者对话树
│   │   ├── npc_blacksmith.json              # 铁匠对话树
│   │   ├── npc_merchant.json                # 商人对话树
│   │   └── lore_items.json                  # 物品描述/世界观碎片文本
│   │
│   └── balance/                             # 数值平衡配置
│       ├── level_curve.json                 # 升级所需灵魂碎片曲线
│       ├── damage_formula.json              # 伤害公式系数配置
│       ├── status_effect_values.json        # 状态异常数值（持续时间/爆发伤害等）
│       └── loot_tables.json                 # 掉落概率表
│
├── assets/                                  # 资源文件层
│   ├── sprites/                             # 精灵图/精灵表
│   │   ├── player/                          # 玩家角色各武器形态精灵表
│   │   ├── enemies/                         # 各类敌人精灵表
│   │   ├── bosses/                          # Boss 精灵表
│   │   ├── npc/                             # NPC 精灵表
│   │   ├── weapons/                         # 武器图标和攻击特效精灵
│   │   ├── items/                           # 物品图标精灵
│   │   └── effects/                         # 粒子/技能特效精灵表
│   │
│   ├── tilesets/                            # 瓦片素材集
│   │   ├── graveyard_tileset.png            # 古墓地带瓦片图集
│   │   ├── swamp_tileset.png
│   │   ├── ironmine_tileset.png
│   │   ├── darkforest_tileset.png
│   │   └── castle_tileset.png
│   │
│   ├── ui/                                  # UI 图片资源
│   │   ├── hud_frames.png                   # HUD 框体图
│   │   ├── icons/                           # 各类图标（状态/武器/物品）
│   │   ├── fonts/                           # 字体文件（.ttf）
│   │   └── backgrounds/                     # 主菜单/加载界面背景图
│   │
│   └── audio/                               # 音频资源
│       ├── bgm/                             # 各区域背景音乐（.ogg）
│       ├── sfx/                             # 音效文件（攻击/受伤/技能/环境）
│       └── voice/                           # NPC 语音（可选，.ogg）
│
├── save/                                    # 存档系统层
│   ├── __init__.py
│   ├── save_manager.py                      # 存档管理器（序列化/反序列化/多存档槽）
│   ├── save_data.py                         # 存档数据结构定义（玩家状态/地图进度/物品）
│   └── slots/                               # 存档文件目录（运行时生成）
│       ├── slot_1.sav
│       ├── slot_2.sav
│       └── slot_3.sav
│
├── utils/                                   # 工具层（通用工具函数）
│   ├── __init__.py
│   ├── math_utils.py                        # 数学工具（向量运算/角度/距离/插值）
│   ├── rect_utils.py                        # 矩形工具（碰撞检测辅助/裁剪）
│   ├── json_loader.py                       # JSON 数据加载器（缓存/路径统一管理）
│   ├── resource_cache.py                    # 资源缓存池（图片/音频避免重复加载）
│   ├── timer.py                             # 计时器工具（冷却/持续时间/延迟触发）
│   ├── state_machine.py                     # 通用有限状态机基类（供各模块复用）
│   ├── color.py                             # 颜色常量定义（游戏中常用颜色值）
│   └── debug.py                             # 调试工具（碰撞箱可视化/FPS显示/日志）
│
└── tests/                                   # 测试层
    ├── __init__.py
    ├── test_damage_calculator.py            # 伤害计算器单元测试
    ├── test_status_effects.py               # 状态异常逻辑测试
    ├── test_ai_state_machine.py             # 敌人 AI 状态机测试
    ├── test_collision.py                    # 碰撞检测测试
    ├── test_save_load.py                    # 存档读写测试
    └── test_combat_system.py               # 战斗系统集成测试
```

---

## 架构分层说明

```
┌─────────────────────────────────────────────┐
│                   scenes/                   │  ← 场景层：各功能界面调度
├──────────┬──────────┬───────────┬───────────┤
│ entities │  combat  │  weapons  │   items   │  ← 游戏对象层
├──────────┴──────────┴───────────┴───────────┤
│              systems/ + map/                │  ← 规则/世界层
├─────────────────────────────────────────────┤
│        physics/ + animation/ + audio/       │  ← 表现/模拟层
├─────────────────────────────────────────────┤
│                    core/                    │  ← 引擎底层
├─────────────────────────────────────────────┤
│               data/ + assets/               │  ← 数据/资源层（驱动上层）
└─────────────────────────────────────────────┘
```

---

## 关键设计原则

| 原则 | 体现 |
|---|---|
| **数据驱动** | 所有数值配置放在 `data/` 的 JSON 文件中，改数值不改代码 |
| **组件解耦** | `combat/` 与 `entities/` 分离，战斗逻辑不污染实体本身 |
| **状态机统一** | `utils/state_machine.py` 作为基类，玩家/敌人/动画共用一套框架 |
| **资源缓存** | `utils/resource_cache.py` 避免每帧重复加载图片/音频 |
| **场景管理** | 栈式场景管理，暂停/营地等界面叠加而不销毁游戏场景 |


# 《烬土传说》工程代码开发顺序

> 遵循 **从底层到上层、从核心到外围、从单机制到完整系统** 的原则，确保每个阶段都可运行和测试。

---

## 第一阶段：工程基础搭建

**目标：跑通一个空白窗口，确立整个项目的技术骨架**

1. `requirements.txt` —— 确定依赖库（pygame 等），完成环境搭建
2. `config.py` —— 定义全局常量（分辨率、帧率、颜色、路径根目录）
3. `utils/color.py` —— 颜色常量
4. `utils/math_utils.py` —— 向量、距离等基础数学工具
5. `utils/timer.py` —— 计时器工具（后续冷却/持续时间大量使用）
6. `utils/state_machine.py` —— 通用有限状态机基类（全局复用）
7. `utils/json_loader.py` —— JSON 数据加载器（后续数据驱动的基础）
8. `utils/resource_cache.py` —— 资源缓存池（图片/音频加载管理）
9. `utils/debug.py` —— 调试工具（碰撞框可视化/FPS/日志，全程调试用）
10. `utils/rect_utils.py` —— 矩形辅助工具
11. `core/clock.py` —— 游戏时钟，delta_time 管理
12. `core/event_manager.py` —— 全局事件总线
13. `core/input_handler.py` —— 键盘/手柄输入统一管理
14. `core/renderer.py` —— 渲染器基础框架（分层绘制）
15. `core/camera.py` —— 摄像机（跟随/视口裁剪/震动）
16. `core/scene_manager.py` —— 场景管理器（入栈/出栈/切换）
17. `scenes/base_scene.py` —— 场景基类接口定义
18. `core/game.py` —— 游戏主类，整合以上模块，跑通主循环
19. `main.py` —— 程序入口，启动游戏主循环

---

## 第二阶段：地图与物理基础

**目标：渲染出可行走的 2.5D 地图，玩家能在地图上移动**

20. `map/tile.py` —— 瓦片基础数据类（类型/碰撞标记/前景标记）
21. `map/tile_map.py` —— 瓦片地图加载与渲染
22. `map/collision_map.py` —— 静态碰撞地图构建
23. `map/layer_renderer.py` —— 分层渲染（背景/地面/前景遮挡）
24. `data/maps/area_graveyard/tilemap.json` —— 第一张测试地图数据
25. `physics/gravity.py` —— 重力与跳跃基础
26. `physics/collision_detector.py` —— AABB 碰撞检测
27. `physics/movement_resolver.py` —— 移动+碰撞响应解算
28. `map/platform.py` —— 单向平台逻辑
29. `map/trap.py` —— 环境陷阱基础（触碰扣血）
30. `map/transition_gate.py` —— 区域传送门触发逻辑
31. `map/campfire.py` —— 营地篝火对象（激活/交互触发）
32. `map/area.py` —— 区域容器类（地图+实体+营地）
33. `map/world_map.py` —— 世界地图管理与区域解锁

---

## 第三阶段：玩家基础系统

**目标：玩家能在地图上完整移动、跳跃、翻滚**

34. `data/entities/player_base_stats.json` —— 玩家初始属性数据
35. `entities/base_entity.py` —— 实体基类（位置/碰撞箱/生命周期）
36. `entities/player/player_stats.py` —— 玩家属性数据类
37. `entities/player/player_state_machine.py` —— 玩家状态机（Idle/Run/Jump/Fall/Roll/Dead）
38. `entities/player/player_controller.py` —— 玩家输入控制（移动/跳跃/翻滚）
39. `animation/animation_clip.py` —— 动画片段数据结构
40. `animation/sprite_sheet_loader.py` —— 精灵表切割与缓存
41. `animation/animation_state_machine.py` —— 动画状态机
42. `animation/animator.py` —— 动画控制器（与玩家状态机联动）
43. `entities/player/player.py` —— 玩家主类整合（移动+动画+状态机）

---

## 第四阶段：战斗核心系统

**目标：玩家能发出带判定的攻击，伤害体系跑通**

44. `combat/hitbox.py` —— 攻击判定框（生命周期/位置绑定）
45. `combat/damage_calculator.py` —— 伤害计算公式实现
46. `combat/knockback.py` —— 击退物理计算
47. `combat/poise_system.py` —— 韧性与硬直触发
48. `combat/combo_system.py` —— 连段窗口与攻击衔接
49. `combat/parry_system.py` —— 弹反窗口检测与触发
50. `combat/status_effects.py` —— 各状态异常效果实现（流血/中毒/燃烧/冰冻/诅咒/眩晕）
51. `combat/status_effect_manager.py` —— 状态异常的挂载/更新/移除管理
52. `data/balance/damage_formula.json` —— 伤害公式系数配置
53. `data/balance/status_effect_values.json` —— 状态异常数值配置
54. `entities/player/player_combat.py` —— 玩家战斗逻辑（攻击/格挡/弹反/处决）
55. `physics/projectile.py` —— 抛射物物理（箭矢/魔法弹轨迹）

---

## 第五阶段：武器系统

**目标：玩家可持有不同武器，各武器有独立攻击方式和战技**

56. `weapons/affixes/elemental_enchant.py` —— 元素附魔词条
57. `weapons/affixes/lifesteal.py` —— 吸血词条
58. `weapons/affixes/swift.py` —— 迅捷词条
59. `weapons/affixes/armor_break.py` —— 破甲词条
60. `weapons/affixes/status_boost.py` —— 状态强化词条
61. `weapons/weapon_art.py` —— 战技系统基类
62. `weapons/base_weapon.py` —— 武器基类（整合属性/词条/战技）
63. `weapons/types/dagger.py` —— 匕首（最简单先实现，含幻影步）
64. `weapons/types/sword.py` —— 单手剑（含旋风斩）
65. `weapons/types/greatsword.py` —— 大剑（含天崩地裂）
66. `weapons/types/spear.py` —— 长矛（含格挡反击）
67. `weapons/types/axe.py` —— 战斧（含破盾特性）
68. `weapons/types/bow.py` —— 弓（含穿云箭/弹药消耗）
69. `weapons/types/staff.py` —— 法杖（含魔法弹幕）
70. `weapons/types/holy_tome.py` —— 圣典（含治疗+神圣）
71. `data/weapons/` —— 各武器类型 JSON 数据文件
72. `weapons/weapon_upgrade.py` —— 武器强化系统（+1~+10/路线）

---

## 第六阶段：物品与背包系统

**目标：玩家可拾取/持有/使用各类消耗品和装备**

73. `items/base_item.py` —— 物品基类
74. `items/consumables/heal_potion.py` —— HP 恢复消耗品
75. `items/consumables/mana_potion.py` —— Mana 恢复消耗品
76. `items/consumables/stamina_potion.py` —— Stamina 恢复消耗品
77. `items/consumables/antidote.py` —— 万能解药
78. `items/consumables/buff_items.py` —— 强化类消耗品
79. `items/consumables/special_items.py` —— 特殊消耗品（传送石/炸弹/飞镖/骨灰）
80. `items/consumables/arrow.py` —— 箭矢弹药
81. `items/equipment/armor.py` —— 护甲物品数据类
82. `items/equipment/set_bonus.py` —— 套装效果计算
83. `items/special/boss_soul.py` —— 灵核物品
84. `items/special/upgrade_material.py` —— 强化材料
85. `items/item_manager.py` —— 物品生成/掉落/拾取管理
86. `data/items/` —— 消耗品/护甲/材料 JSON 数据文件
87. `entities/player/player_inventory.py` —— 玩家背包系统（武器/护甲/消耗品槽位管理）

---

## 第七阶段：敌人 AI 系统

**目标：不同类型的敌人能自主巡逻、发现并追击玩家、发动攻击**

88. `data/entities/enemies/` —— 各敌人属性 JSON 数据文件
89. `entities/enemies/enemy_stats.py` —— 敌人属性数据类
90. `entities/enemies/enemy_ai.py` —— 核心 AI 状态机（巡逻/警戒/追击/战斗/回归）
91. `entities/enemies/base_enemy.py` —— 敌人基类（整合属性+AI+动画）
92. `entities/enemies/types/infantry.py` —— 普通步兵实现
93. `entities/enemies/types/heavy_armor.py` —— 重甲兵实现
94. `entities/enemies/types/archer.py` —— 弓箭手实现
95. `entities/enemies/types/mage.py` —— 法师实现（含吟唱打断）
96. `entities/enemies/types/undead.py` —— 不死类实现（含复活逻辑）
97. `entities/enemies/types/beast.py` —— 野兽类实现（高速连击）
98. `entities/enemies/types/elite.py` —— 精英兵实现
99. `data/balance/loot_tables.json` —— 掉落概率表
100. `systems/loot_system.py` —— 掉落系统（概率计算/物品生成）
101. `entities/enemies/enemy_spawner.py` —— 敌人生成器（读取地图配置生成敌人）
102. `data/maps/area_graveyard/enemy_spawns.json` —— 第一区域敌人配置

---

## 第八阶段：游戏规则核心系统

**目标：灵魂碎片、死亡惩罚、营地补充、升级成长等核心规则跑通**

103. `systems/soul_fragment_system.py` —— 灵魂碎片掉落/遗物生成/捡回/永久消失
104. `systems/respawn_system.py` —— 死亡复活（营地复活+敌人重置）
105. `systems/campfire_system.py` —— 营地系统（消耗品补充/传送网络）
106. `data/balance/level_curve.json` —— 升级经验曲线配置
107. `systems/progression_system.py` —— 升级成长系统（灵魂碎片消耗/属性点分配）
108. `systems/upgrade_system.py` —— 武器强化系统逻辑（材料消耗/等级/路线）
109. `systems/quest_system.py` —— 游戏进度系统（Boss 击杀记录/区域解锁管理）

---

## 第九阶段：Boss 系统

**目标：实现完整的 Boss 战体验（两阶段、专属机制、专属奖励）**

110. `data/entities/bosses/` —— 各 Boss 属性与技能 JSON 数据文件
111. `entities/enemies/bosses/base_boss.py` —— Boss 基类（两阶段/怒气值/硬直抗性）
112. `entities/enemies/bosses/duke_rotbone.py` —— Boss①：腐骨公爵
113. `entities/enemies/bosses/witch_mora.py` —— Boss②：沼泽女巫
114. `entities/enemies/bosses/lord_berg.py` —— Boss③：锤神伯格
115. `entities/enemies/bosses/assassin_ella.py` —— Boss④：幽魂艾拉
116. `entities/enemies/bosses/dragon_aegnis.py` —— 终章 Boss：堕落龙

---

## 第十阶段：NPC 与对话系统

**目标：营地 NPC 可交互，对话/强化/购买等功能完整**

117. `data/dialogues/` —— 各 NPC 对话树 JSON 数据
118. `entities/npc/base_npc.py` —— NPC 基类（交互范围/对话触发）
119. `entities/npc/keeper.py` —— 营地守护者（升级/传送/剧情）
120. `entities/npc/blacksmith.py` —— 铁匠（武器强化）
121. `entities/npc/merchant.py` —— 商人（消耗品购买/出售）

---

## 第十一阶段：粒子特效与音频

**目标：战斗反馈更丰富，区域有专属背景音乐**

122. `animation/particle_system.py` —— 粒子特效（血溅/火焰/魔法光效/灰尘）
123. `audio/sfx_player.py` —— 音效播放器（攻击/受伤/环境音）
124. `audio/bgm_player.py` —— 背景音乐播放器（淡入淡出/区域切换）
125. `audio/audio_manager.py` —— 音频统一管理入口
126. `assets/audio/` —— 导入音频资源文件

---

## 第十二阶段：UI 系统

**目标：游戏内所有界面完整可用**

127. `ui/font_manager.py` —— 字体管理器（优先实现，其他 UI 依赖）
128. `ui/base_widget.py` —— UI 控件基类
129. `ui/damage_number.py` —— 飘字伤害数字
130. `ui/notification.py` —— 浮动提示信息
131. `ui/hud.py` —— 游戏内 HUD（HP/Stamina/Mana 条）
132. `ui/boss_healthbar.py` —— Boss 专属双阶段血条
133. `ui/dialogue_box.py` —— NPC 对话框
134. `ui/inventory_panel.py` —— 背包界面
135. `ui/equipment_panel.py` —— 装备栏界面
136. `ui/status_panel.py` —— 人物属性界面
137. `ui/campfire_menu.py` —— 营地菜单 UI
138. `ui/death_screen.py` —— 死亡界面
139. `ui/loading_screen.py` —— 加载界面
140. `ui/pause_menu_ui.py` —— 暂停菜单
141. `ui/settings_ui.py` —— 设置界面
142. `ui/main_menu_ui.py` —— 主菜单界面

---

## 第十三阶段：场景整合

**目标：各功能场景完整串联，游戏流程完整跑通**

143. `scenes/loading_scene.py` —— 加载过渡场景
144. `scenes/game_scene.py` —— 核心游戏场景（整合地图/实体/战斗/UI）
145. `scenes/boss_scene.py` —— Boss 战斗专用场景
146. `scenes/campfire_scene.py` —— 营地交互场景
147. `scenes/game_over_scene.py` —— 死亡/游戏结束场景
148. `scenes/pause_scene.py` —— 暂停菜单场景
149. `scenes/settings_scene.py` —— 设置场景
150. `scenes/main_menu_scene.py` —— 主菜单场景

---

## 第十四阶段：存档系统

**目标：游戏进度可保存和读取**

151. `save/save_data.py` —— 存档数据结构定义
152. `save/save_manager.py` —— 存档序列化/反序列化/多槽位管理

---

## 第十五阶段：剩余地图内容制作

**目标：补全世界观所有区域地图和配套数据**

153. `data/maps/area_swamp/` —— 毒沼泽地图数据
154. `data/maps/area_ironmine/` —— 铁山矿场地图数据
155. `data/maps/area_darkforest/` —— 黑暗森林地图数据
156. `data/maps/area_castle/` —— 堕落王城地图数据
157. `assets/tilesets/` —— 各区域瓦片素材导入
158. `assets/sprites/` —— 全部精灵图资源导入整理

---

## 第十六阶段：数值平衡与测试

**目标：游戏体验调优，确保难度曲线合理**

159. `data/balance/` —— 反复调整所有数值配置文件
160. `tests/test_damage_calculator.py` —— 伤害计算单元测试
161. `tests/test_status_effects.py` —— 状态异常逻辑测试
162. `tests/test_ai_state_machine.py` —— 敌人 AI 状态机测试
163. `tests/test_collision.py` —— 碰撞检测测试
164. `tests/test_save_load.py` —— 存档读写测试
165. `tests/test_combat_system.py` —— 战斗系统集成测试

---

## 开发阶段总览

| 阶段 | 核心交付物 | 可验证内容 |
|---|---|---|
| 第一阶段 | 工程骨架 | 空白窗口正常启动 |
| 第二阶段 | 地图与物理 | 在地图上行走/跳跃 |
| 第三阶段 | 玩家基础 | 玩家移动+动画正常 |
| 第四阶段 | 战斗核心 | 攻击有判定/伤害可计算 |
| 第五阶段 | 武器系统 | 不同武器攻击方式不同 |
| 第六阶段 | 物品背包 | 可拾取使用消耗品 |
| 第七阶段 | 敌人 AI | 敌人能追击并攻击玩家 |
| 第八阶段 | 规则系统 | 死亡/复活/升级流程完整 |
| 第九阶段 | Boss 系统 | Boss 两阶段战斗完整 |
| 第十阶段 | NPC 对话 | 营地功能全部可用 |
| 第十一阶段 | 特效音频 | 战斗有音效和粒子反馈 |
| 第十二阶段 | UI 界面 | 所有界面完整可交互 |
| 第十三阶段 | 场景串联 | 游戏全流程可跑通 |
| 第十四阶段 | 存档系统 | 进度可保存读取 |
| 第十五阶段 | 内容补全 | 全部区域地图完整 |
| 第十六阶段 | 平衡测试 | 难度曲线合理，无重大 Bug |