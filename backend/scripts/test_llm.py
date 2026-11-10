"""4.1 LLM 接入验证脚本：测试能否成功调用配置的大模型。

用法：
    cd backend
    uv run python scripts/test_llm.py
"""

from app.llm import get_llm


def main():
    llm = get_llm()
    if llm is None:
        print("❌ LLM 未初始化，请检查 langchain-openai 是否已安装")
        return

    print(f"正在调用模型...")
    try:
        resp = llm.invoke("用一句话介绍你自己，并告诉我你现在是什么模型。")
        print("✅ 调用成功！")
        print("-" * 50)
        print(resp.content if hasattr(resp, "content") else resp)
        print("-" * 50)
    except Exception as e:
        print("❌ 调用失败，错误信息：")
        print(f"   类型: {type(e).__name__}")
        print(f"   内容: {e}")


if __name__ == "__main__":
    main()
