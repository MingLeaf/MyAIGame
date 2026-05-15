"""
NPC 对话调试启动器
运行此脚本启动游戏，对话相关日志写入 __dialogue_log.txt
"""
import os, sys, logging, datetime

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__dialogue_log.txt")

# 配置日志
logging.basicConfig(
    filename=LOG_PATH,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# 写文件头
with open(LOG_PATH, "a", encoding="utf-8") as f:
    pass  # basicConfig 已经创建了文件

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"启动游戏中... 日志: {LOG_PATH}")
print("与铁匠或商人对话触发闪退后，关闭游戏，告诉 AI 读取 __dialogue_log.txt")

from Main import main

try:
    main()
except Exception as e:
    import traceback
    tb = traceback.format_exc()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n\n=== FATAL CRASH ===\n{tb}\n")
    print(tb)
