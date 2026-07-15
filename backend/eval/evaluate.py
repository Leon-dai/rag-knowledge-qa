"""RAGAS 评估脚本

参考 All-in-RAG Chapter 7 — RAG 系统评估方法论

评估指标：
1. Faithfulness（忠实度）：回答是否忠于检索到的文档
2. Answer Relevancy（答案相关性）：回答是否切题
3. Context Precision（上下文精确度）：检索文档中相关文档的占比
4. Context Recall（上下文召回率）：应该被检索到的文档实际被检索到了多少
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# 测试数据集（示例）
TEST_CASES = [
    {
        "question": "iPhone 15 Pro 的摄像头参数是什么？",
        "ground_truth": "iPhone 15 Pro 配备 4800 万像素主摄、1200 万像素超广角和 1200 万像素长焦摄像头。",
    },
    {
        "question": "如何办理退货？",
        "ground_truth": "用户可在收货后 7 天内申请退货，需保持商品完好，通过 APP 提交退货申请。",
    },
    {
        "question": "产品价格包含税费吗？",
        "ground_truth": "是的，所有标注价格均为含税价，无需额外支付税费。",
    },
    {
        "question": "保修期多久？",
        "ground_truth": "产品享受 1 年官方保修服务，保修期内非人为损坏免费维修。",
    },
    {
        "question": "支持哪些支付方式？",
        "ground_truth": "支持支付宝、微信支付、银行卡、信用卡等多种支付方式。",
    },
]


async def run_rag_query(question: str) -> dict:
    """运行 RAG 查询并返回结果

    Returns:
        {
            "answer": str,
            "contexts": list[str],
        }
    """
    from app.rag.service import RAGService

    # 收集流式响应
    full_answer = ""
    contexts = []

    async for chunk in RAGService.query(question, chat_history=[]):
        # 解析 SSE 数据
        if chunk.startswith("data: "):
            try:
                data = json.loads(chunk[6:])
                if "token" in data:
                    full_answer += data["token"]
                elif "sources" in data:
                    contexts = [
                        source.get("content", "")
                        for source in data["sources"]
                        if source.get("content")
                    ]
            except json.JSONDecodeError:
                continue

    return {
        "answer": full_answer,
        "contexts": contexts,
    }


def evaluate_with_ragas(test_results: list[dict]) -> dict:
    """使用 RAGAS 框架评估结果

    Args:
        test_results: 测试结果列表，每项包含:
            - question: 问题
            - answer: 生成的答案
            - contexts: 检索到的上下文
            - ground_truth: 标准答案

    Returns:
        评估指标字典
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset

        # 准备评估数据
        eval_data = {
            "question": [r["question"] for r in test_results],
            "answer": [r["answer"] for r in test_results],
            "contexts": [r["contexts"] for r in test_results],
            "ground_truth": [r["ground_truth"] for r in test_results],
        }

        dataset = Dataset.from_dict(eval_data)

        # 运行评估
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        return results

    except ImportError as e:
        print(f"⚠️  RAGAS 未安装，跳过评估: {e}")
        print("💡 安装命令: pip install ragas")
        return None
    except Exception as e:
        print(f"⚠️  评估失败: {e}")
        return None


def generate_report(test_results: list[dict], eval_results: dict | None) -> str:
    """生成评估报告（Markdown 格式）

    Args:
        test_results: 测试结果
        eval_results: RAGAS 评估结果

    Returns:
        Markdown 格式的报告
    """
    report = []
    report.append("# RAG 系统评估报告\n")
    report.append(f"评估时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"测试用例数：{len(test_results)}\n\n")

    # 测试用例详情
    report.append("## 测试用例详情\n")
    for i, result in enumerate(test_results, 1):
        report.append(f"### 用例 {i}\n")
        report.append(f"**问题**：{result['question']}\n\n")
        report.append(f"**标准答案**：{result['ground_truth']}\n\n")
        report.append(f"**生成答案**：{result['answer'][:500]}{'...' if len(result['answer']) > 500 else ''}\n\n")
        report.append(f"**检索上下文数**：{len(result['contexts'])}\n\n")
        report.append("---\n\n")

    # 评估指标
    if eval_results:
        report.append("## RAGAS 评估指标\n\n")
        report.append("| 指标 | 分数 | 说明 |\n")
        report.append("|------|------|------|\n")
        report.append(f"| Faithfulness | {eval_results.get('faithfulness', 0):.3f} | 回答是否忠于检索文档 |\n")
        report.append(f"| Answer Relevancy | {eval_results.get('answer_relevancy', 0):.3f} | 回答是否切题 |\n")
        report.append(f"| Context Precision | {eval_results.get('context_precision', 0):.3f} | 检索文档精确度 |\n")
        report.append(f"| Context Recall | {eval_results.get('context_recall', 0):.3f} | 检索文档召回率 |\n")
        report.append("\n")

        # 综合评分
        avg_score = sum([
            eval_results.get('faithfulness', 0),
            eval_results.get('answer_relevancy', 0),
            eval_results.get('context_precision', 0),
            eval_results.get('context_recall', 0),
        ]) / 4
        report.append(f"**综合评分**：{avg_score:.3f}\n")

    return "\n".join(report)


async def main():
    """主函数：运行评估"""
    print("=" * 60)
    print("🚀 RAG 系统评估开始")
    print("=" * 60)

    # 1. 运行测试用例
    print("\n📝 运行测试用例...")
    test_results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test_case['question']}")
        result = await run_rag_query(test_case["question"])
        test_results.append({
            "question": test_case["question"],
            "ground_truth": test_case["ground_truth"],
            "answer": result["answer"],
            "contexts": result["contexts"],
        })
        print(f"  ✓ 答案长度: {len(result['answer'])} 字符")
        print(f"  ✓ 检索上下文: {len(result['contexts'])} 条")

    # 2. 保存测试结果
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 测试结果已保存: {results_file}")

    # 3. 运行 RAGAS 评估
    print("\n📊 运行 RAGAS 评估...")
    eval_results = evaluate_with_ragas(test_results)

    if eval_results:
        print(f"  ✓ Faithfulness: {eval_results.get('faithfulness', 0):.3f}")
        print(f"  ✓ Answer Relevancy: {eval_results.get('answer_relevancy', 0):.3f}")
        print(f"  ✓ Context Precision: {eval_results.get('context_precision', 0):.3f}")
        print(f"  ✓ Context Recall: {eval_results.get('context_recall', 0):.3f}")

        # 保存评估结果
        eval_file = Path(__file__).parent / "eval_results.json"
        with open(eval_file, "w", encoding="utf-8") as f:
            json.dump(eval_results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 评估结果已保存: {eval_file}")

    # 4. 生成报告
    print("\n📄 生成评估报告...")
    report = generate_report(test_results, eval_results)
    report_file = Path(__file__).parent / "evaluation_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"💾 报告已保存: {report_file}")

    print("\n" + "=" * 60)
    print("✅ RAG 系统评估完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
