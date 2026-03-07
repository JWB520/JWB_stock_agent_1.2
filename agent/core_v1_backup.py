"""
主控智能体核心模块：负责意图识别、多步推理、工具调度及记忆流转。
该模块通过 Function Calling 循环实现“思考-行动-观察”的 Agent 链路。
"""
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# 导入本地工程模块
from agent.memory import Memory
from agent.prompts import SYSTEM_PROMPT
from tools.akshare_tools import TOOL_MAP, TOOLS
from utils.logger import logger, log_llm_request, log_llm_response, log_tool_call, log_tool_result

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端 (对接 DeepSeek)
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

class Agent:
    def __init__(self, model: str = "deepseek-chat", max_iterations: int = 10):
        """
        初始化智能体
        :param model: 使用的大模型名称
        :param max_iterations: 最大推理轮数，防止死循环并支持深度复盘
        """
        self.model = model
        self.memory = Memory()
        self.max_iterations = max_iterations

    def _call_tool(self, name: str, args: dict) -> str:
        """
        执行具体的工具函数并记录日志
        """
        func = TOOL_MAP.get(name)
        if not func:
            return json.dumps({"status": "error", "message": f"未知工具: {name}"}, ensure_ascii=False)
        
        t0 = log_tool_call(name, args)
        try:
            # 执行 AkShare 封装工具
            result = func(**args)
            log_tool_result(name, t0, "ok")
            return result
        except Exception as e:
            error_msg = f"工具执行异常: {str(e)}"
            log_tool_result(name, t0, "error", error_msg)
            return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)

    def run(self, user_input: str) -> str:
        """
        Agent 主运行循环
        """
        # 1. 记录用户输入并注入当前时间锚点
        self.memory.add("user", user_input)
        
        # 注入系统时间，防止模型在日期推算上产生幻觉
        curr_time = datetime.now().strftime("%Y年%m月%d日，星期%w")
        time_injection = f"【系统时间注入：今天是 {curr_time}】\n"
        
        # 组装完整消息上下文
        messages = [{"role": "system", "content": time_injection + SYSTEM_PROMPT}] + self.memory.get()

        # 2. 进入多步推理循环 (ReAct 模式)
        for i in range(self.max_iterations):
            log_llm_request(messages, TOOLS)
            
            # 请求大模型
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            
            msg = resp.choices[0].message
            usage = resp.usage
            
            # 记录 Token 消耗
            if usage:
                logger.info("Token消耗 | Iteration %d | prompt=%d completion=%d total=%d",
                            i+1, usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)
            
            log_llm_response(msg.content, msg.tool_calls)

            # 如果模型不再需要调用工具，说明推理完成
            if not msg.tool_calls:
                self.memory.add("assistant", msg.content)
                return msg.content

            # 3. 执行工具调用请求
            # 首先将模型的“思考（Tool Calls）”写入上下文
            messages.append(msg)
            self.memory.append_raw(msg)

            for tc in msg.tool_calls:
                # 尝试解析参数
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as e:
                    logger.warning("Tool参数解析失败 [%s]: %s", tc.function.name, e)
                    tool_result = json.dumps({"status": "error", "message": "JSON格式错误，请检查参数结构"}, ensure_ascii=False)
                    args = None

                if args is not None:
                    # 调用实际工具
                    tool_result = self._call_tool(tc.function.name, args)
                
                # ---------------------------------------------------------
                # 实时 Debug 打印：曝光底层数据流，辅助开发者监控数据准确性
                # ---------------------------------------------------------
                tool_result_str = str(tool_result)
                preview = tool_result_str[:300] + ("..." if len(tool_result_str) > 300 else "")
                print(f"\n[🔧 Debug] 工具 {tc.function.name} 返回原始数据截取:")
                print(f"{preview}")
                print("-" * 60)

                # 将工具执行结果作为 Observation 塞回消息序列
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result_str
                }
                messages.append(tool_msg)
                self.memory.append_raw(tool_msg)

        # 4. 熔断处理
        final_reply = "⚠️ 推理链路过长，已达到最大迭代次数。建议您细化指令或拆分问题。"
        logger.warning("Agent熔断: 达到最大迭代次数 %d", self.max_iterations)
        self.memory.add("assistant", final_reply)
        return final_reply