import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agent.orchestrator import Orchestrator


def main():
    print("=" * 50)
    print("🚀 A股多智能体研究组 (情报官->分析师->主编 + 评委) 已就绪")
    print('💡 提示：你可以随意使用"昨天"、"上周五"或"20260306"等时间描述。你可以询问任何问题')
    print("=" * 50)

    orchestrator = Orchestrator()

    while True:
        try:
            user_input = input("\n[操盘指令] > ")
            if user_input.lower() in ["exit", "quit"]:
                print("\n系统关闭，空仓也是一种操作！")
                break
            if not user_input.strip():
                continue

            print("\n[多智能体协作推演中... 请稍候]")
            response = orchestrator.run(user_input)
            print("\n" + "=" * 20 + " 深度复盘研报 " + "=" * 20)
            print(response)
            print("=" * 54)

        except KeyboardInterrupt:
            print("\n[中断] 用户手动强制停止当前任务。")
            continue
        except Exception as e:
            print(f"\n[系统崩溃] 发生未捕获异常: {e}")


if __name__ == "__main__":
    main()
