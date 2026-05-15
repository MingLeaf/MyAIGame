# =============================================================
# entities/npc/__init__.py —— NPC 模块入口
# 第 10 阶段：NPC 与对话系统
# =============================================================

from entities.npc.base_npc   import BaseNPC, create_npc
from entities.npc.keeper     import KeeperNPC
from entities.npc.blacksmith import BlacksmithNPC
from entities.npc.merchant   import MerchantNPC

_NPC_REGISTRY = {
    "keeper":     KeeperNPC,
    "blacksmith": BlacksmithNPC,
    "merchant":   MerchantNPC,
}
