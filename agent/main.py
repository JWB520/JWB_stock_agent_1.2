import sys
from pathlib import Path

# 确保 Python 能找到项目根目录下的模块
sys.path.append(str(Path(__file__).parent.parent))

from agent.core import Agent

def main():
    print("="*50)
    print("🚀 A股游资复盘智能体已启动 (纯自然语言交互模式)")
    print("💡 提示：你可以随意使用“昨天”、“上周五”或“20260306”等时间描述。")
    print("="*50)

    # 初始化智能体
    agent = Agent(model="deepseek-chat") 

    while True:
        try:
            # 纯粹的自然语言输入，不再有任何烦人的日期确认！
            user_input = input("\n[操盘指令] > ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("\n系统关闭，空仓也是一种操作！")
                break
            
            if not user_input.strip():
                continue

            print("\n[智能体深度推演与数据抓取中... 请稍候]")
            
            # 直接把用户的自然语言原封不动扔给大模型
            response = agent.run(user_input)
            
            print("\n" + "="*20 + " 深度复盘研报 " + "="*20)
            print(response)
            print("="*54)

        except KeyboardInterrupt:
            print("\n[中断] 用户手动强制停止当前任务。")
            continue
        except Exception as e:
            print(f"\n[系统崩溃] 发生未捕获异常: {e}")

if __name__ == "__main__":
    main()