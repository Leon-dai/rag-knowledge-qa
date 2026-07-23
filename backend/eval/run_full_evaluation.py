"""新知道 - 检索质量完整评估脚本
基线测试 + A/B对比 + Bad Case收集
"""
import asyncio
import json
import sys
import time
import re
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.service import RAGService
from app.rag.retriever import hybrid_search, similarity_search_with_score
from app.rag.reranker import rerank
from app.rag.query_rewriter import smart_rewrite_query


# ============================================================
# 测试用例（基于真实知识库内容设计）
# ============================================================

TEST_CASES = [
    # --- test_product.txt: iPhone 15 Pro ---
    {"id": 1, "question": "iPhone 15 Pro 搭载什么芯片？", "ground_truth": "A17 Pro芯片", "type": "精确查询", "expected_doc": "test_product.txt"},
    {"id": 2, "question": "iPhone 15 Pro 的摄像头像素是多少？", "ground_truth": "4800万像素主摄像头", "type": "精确查询", "expected_doc": "test_product.txt"},
    {"id": 3, "question": "iPhone 15 Pro 多少钱？", "ground_truth": "8999元起", "type": "精确查询", "expected_doc": "test_product.txt"},
    {"id": 4, "question": "iPhone 15 Pro 电池续航多久？", "ground_truth": "最长23小时", "type": "精确查询", "expected_doc": "test_product.txt"},
    {"id": 5, "question": "iPhone 15 Pro 用的什么接口？", "ground_truth": "USB-C接口", "type": "精确查询", "expected_doc": "test_product.txt"},
    {"id": 6, "question": "iPhone 15 Pro 的机身材质是什么？", "ground_truth": "钛金属", "type": "精确查询", "expected_doc": "test_product.txt"},
    # --- 离校指南: 精确查询 ---
    {"id": 7, "question": "离校系统网址是什么？", "ground_truth": "http://lxxt.hnu.edu.cn", "type": "精确查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 8, "question": "图书馆的联系方式是什么？", "ground_truth": "0731-88822677", "type": "精确查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 9, "question": "财务处电话是多少？", "ground_truth": "0731-88684712", "type": "精确查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 10, "question": "毕业生最晚什么时候搬离宿舍？", "ground_truth": "6月24日前", "type": "精确查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    # --- 离校指南: 模糊概念/流程 ---
    {"id": 11, "question": "退宿手续怎么办理？", "ground_truth": "验收宿舍家具和水电设施，填写退宿登记本，退还钥匙，搬离宿舍", "type": "模糊概念", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 12, "question": "图书馆手续包括哪些内容？", "ground_truth": "图书清还、欠费清缴、研究生论文提交", "type": "模糊概念", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 13, "question": "助学贷款还款怎么确认？", "ground_truth": "完成助学贷款毕业确认手续", "type": "模糊概念", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 14, "question": "离校需要办理哪些手续？", "ground_truth": "图书馆手续、助学贷款还款、财务处欠费补缴、退宿手续、教材费补缴、毕业去向审核", "type": "模糊概念", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 15, "question": "教材费欠费怎么处理？", "ground_truth": "教材供应中心会自行联系班级完成清缴，在离校系统查看状态即可", "type": "模糊概念", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    # --- 复合/口语化查询 ---
    {"id": 16, "question": "iPhone 15 Pro 的芯片是什么？价格是多少？", "ground_truth": "A17 Pro芯片，8999元起", "type": "复合查询", "expected_doc": "test_product.txt"},
    {"id": 17, "question": "iPhone15Pro屏幕多大刷新率多少？", "ground_truth": "6.1英寸，120Hz ProMotion自适应刷新率", "type": "复合查询", "expected_doc": "test_product.txt"},
    {"id": 18, "question": "苹果15Pro用的什么处理器啊？", "ground_truth": "A17 Pro芯片", "type": "口语化查询", "expected_doc": "test_product.txt"},
    {"id": 19, "question": "毕业了怎么退宿舍？", "ground_truth": "验收宿舍家具和水电，填退宿登记本，退钥匙，搬离", "type": "口语化查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
    {"id": 20, "question": "那个离校系统的网站是什么来着？", "ground_truth": "http://lxxt.hnu.edu.cn", "type": "口语化查询", "expected_doc": "附件1：2026届毕业生离校系统办理指南.docx"},
]


# ============================================================
# LLM-as-Judge 评分
# ============================================================

JUDGE_PROMPT = """你是一个问答质量评估员。根据标准答案，给AI生成的回答打分。

评分规则（每项0-1分）：
1. 忠实度：回答是否只使用了标准答案中的信息？编造扣分，遗漏不扣分
2. 相关性：回答是否直接回应了问题？偏题扣分
3. 完整性：回答是否覆盖了标准答案中的关键信息？
4. 简洁度：回答是否言简意赅？冗余废话扣分

标准答案：{ground_truth}
用户问题：{question}
AI回答：{answer}

请输出JSON格式（不要其他内容）：
{{"忠实度": 0.X, "相关性": 0.X, "完整性": 0.X, "简洁度": 0.X}}"""


def judge_answer(question: str, ground_truth: str, answer: str) -> dict:
    """用 LLM 对单个回答评分"""
    judge_llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
    prompt = JUDGE_PROMPT.format(question=question, ground_truth=ground_truth, answer=answer[:2000])
    try:
        resp = judge_llm.invoke(prompt)
        result = resp.content.strip()
        json_match = re.search(r'\{[^}]+\}', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"    [WARN] scoring failed: {e}")
    return {"忠实度": 0, "相关性": 0, "完整性": 0, "简洁度": 0}


def compute_hit(search_results, expected_doc_title: str) -> dict:
    """计算检索命中率"""
    if not search_results:
        return {"hit": False, "rank": -1, "count": 0}
    for rank, (doc, _score) in enumerate(search_results):
        if expected_doc_title in doc.metadata.get("doc_title", ""):
            return {"hit": True, "rank": rank + 1, "count": len(search_results)}
    return {"hit": False, "rank": -1, "count": len(search_results)}


# ============================================================
# 基线评估
# ============================================================

async def run_baseline():
    """完整链路基线评估"""
    print("=" * 60)
    print("BASELINE: Full pipeline (20 test cases)")
    print("=" * 60)

    results = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/20] Q: {case['question']}")
        print(f"         Type: {case['type']} | Expected: {case['expected_doc']}")

        # Run full RAG query
        full_answer = ""
        search_results = []
        start = time.time()

        async for chunk in RAGService.query(case["question"], chat_history=[], search_mode="local", deep_think=False):
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])
                    if "token" in data:
                        full_answer += data["token"]
                except json.JSONDecodeError:
                    continue

        elapsed = time.time() - start

        # Get retrieval results
        search_results = hybrid_search(case["question"], top_k=8)
        retrieval = compute_hit(search_results, case["expected_doc"])

        # Judge answer quality
        quality = judge_answer(case["question"], case["ground_truth"], full_answer)

        result = {
            "id": case["id"], "question": case["question"], "type": case["type"],
            "ground_truth": case["ground_truth"], "answer": full_answer[:500],
            "hit": retrieval["hit"], "hit_rank": retrieval["rank"],
            "faithfulness": quality["忠实度"], "relevancy": quality["相关性"],
            "completeness": quality["完整性"], "time": round(elapsed, 1),
        }
        results.append(result)

        hit_str = "HIT" if retrieval["hit"] else "MISS"
        print(f"         [{hit_str}] rank={retrieval['rank']} "
              f"| Faith={quality['忠实度']} Relev={quality['相关性']} "
              f"| Time={elapsed:.1f}s")

    return results


# ============================================================
# A/B 对比测试
# ============================================================

def run_ab_full_vs_simple():
    """A/B: 完整混合检索 vs 纯语义检索"""
    print("\n" + "=" * 60)
    print("A/B: Full hybrid search vs Semantic-only")
    print("=" * 60)

    full_hits = 0
    simple_hits = 0

    for i, case in enumerate(TEST_CASES, 1):
        # Full hybrid
        full_results = hybrid_search(case["question"], top_k=8)
        f_hit = compute_hit(full_results, case["expected_doc"])["hit"]

        # Semantic only
        simple_results = similarity_search_with_score(case["question"], k=8)
        simple_results = [(doc, 1.0 - score) for doc, score in simple_results]
        s_hit = compute_hit(simple_results, case["expected_doc"])["hit"]

        full_hits += 1 if f_hit else 0
        simple_hits += 1 if s_hit else 0

        if i <= 3 or f_hit != s_hit:
            print(f"  [{i}] Full={'HIT' if f_hit else 'MISS'} | Semantic={'HIT' if s_hit else 'MISS'} | {case['question'][:50]}")

    print(f"\n  Result: Full={full_hits}/20 | Semantic-only={simple_hits}/20")
    return full_hits, simple_hits


def run_ab_rewrite_vs_no_rewrite():
    """A/B: 有查询改写 vs 无查询改写"""
    print("\n" + "=" * 60)
    print("A/B: With rewrite vs Without rewrite")
    print("=" * 60)

    with_rewrite_hits = 0
    without_rewrite_hits = 0

    for i, case in enumerate(TEST_CASES, 1):
        # With rewrite
        rewritten = smart_rewrite_query(case["question"], [])
        all_docs = {}
        for q in rewritten[:3]:
            results = hybrid_search(q, top_k=5)
            for doc, score in results:
                key = f"{doc.metadata.get('doc_title', '')}:{doc.metadata.get('chunk_index', 0)}"
                if key not in all_docs:
                    all_docs[key] = (doc, score)
        with_results = list(all_docs.values())[:8]
        w_hit = compute_hit(with_results, case["expected_doc"])["hit"]

        # Without rewrite
        raw_results = hybrid_search(case["question"], top_k=8)
        n_hit = compute_hit(raw_results, case["expected_doc"])["hit"]

        with_rewrite_hits += 1 if w_hit else 0
        without_rewrite_hits += 1 if n_hit else 0

        if i <= 3 or w_hit != n_hit:
            print(f"  [{i}] Rewrite={'HIT' if w_hit else 'MISS'} | NoRewrite={'HIT' if n_hit else 'MISS'} | {case['question'][:50]}")

    print(f"\n  Result: WithRewrite={with_rewrite_hits}/20 | NoRewrite={without_rewrite_hits}/20")
    return with_rewrite_hits, without_rewrite_hits


def run_ab_judge_vs_no_judge():
    """A/B: 有AI相关性过滤 vs 无过滤(top-3)"""
    print("\n" + "=" * 60)
    print("A/B: With AI Judge filter vs Without (top-3)")
    print("=" * 60)

    with_judge_hits = 0
    without_judge_hits = 0

    for i, case in enumerate(TEST_CASES, 1):
        search_results = hybrid_search(case["question"], top_k=8)

        # With AI judge filter
        if search_results:
            relevant = RAGService._judge_relevance(case["question"], search_results)
        else:
            relevant = []
        w_hit = compute_hit(relevant, case["expected_doc"])["hit"]

        # Without (just top-3)
        without = [(doc, score) for doc, score in search_results[:3]]
        n_hit = compute_hit(without, case["expected_doc"])["hit"]

        with_judge_hits += 1 if w_hit else 0
        without_judge_hits += 1 if n_hit else 0

        if i <= 3 or w_hit != n_hit:
            print(f"  [{i}] Judge={'HIT' if w_hit else 'MISS'} | Top3={'HIT' if n_hit else 'MISS'} | {case['question'][:50]}")

    print(f"\n  Result: WithJudge={with_judge_hits}/20 | NoJudge={without_judge_hits}/20")
    return with_judge_hits, without_judge_hits


def run_ab_rerank_vs_no_rerank():
    """A/B: 有重排序 vs 无重排序"""
    print("\n" + "=" * 60)
    print("A/B: With Rerank vs Without Rerank")
    print("=" * 60)

    with_rerank_hits = 0
    without_rerank_hits = 0

    for i, case in enumerate(TEST_CASES, 1):
        search_results = hybrid_search(case["question"], top_k=8)

        # After judge filter
        if search_results:
            relevant = RAGService._judge_relevance(case["question"], search_results)
        else:
            relevant = []

        # With rerank
        if relevant:
            reranked = rerank(case["question"], [doc for doc, _ in relevant], top_k=3)
        else:
            reranked = []
        w_hit = compute_hit(reranked, case["expected_doc"])["hit"]

        # Without rerank (just top-3 after judge)
        without = [(doc, score) for doc, score in relevant[:3]] if relevant else []
        n_hit = compute_hit(without, case["expected_doc"])["hit"]

        with_rerank_hits += 1 if w_hit else 0
        without_rerank_hits += 1 if n_hit else 0

        if i <= 3 or w_hit != n_hit:
            print(f"  [{i}] Rerank={'HIT' if w_hit else 'MISS'} | NoRerank={'HIT' if n_hit else 'MISS'} | {case['question'][:50]}")

    print(f"\n  Result: WithRerank={with_rerank_hits}/20 | NoRerank={without_rerank_hits}/20")
    return with_rerank_hits, without_rerank_hits


def collect_bad_cases(baseline_results: list) -> list:
    """收集Bad Case: 忠实度或相关性低于0.6的回答"""
    bad_cases = []
    for r in baseline_results:
        if r["faithfulness"] < 0.6 or r["relevancy"] < 0.6:
            problem = []
            if r["faithfulness"] < 0.6:
                problem.append("faithfulness_low")
            if r["relevancy"] < 0.6:
                problem.append("relevancy_low")

            # Root cause analysis
            if r["hit"]:
                root_cause = "retrieval succeeded but answer generation introduced errors"
            else:
                root_cause = "retrieval failed to find relevant document"

            bad_cases.append({
                "id": r["id"],
                "question": r["question"],
                "type": r["type"],
                "ground_truth": r["ground_truth"],
                "answer": r["answer"],
                "faithfulness": r["faithfulness"],
                "relevancy": r["relevancy"],
                "problem": " + ".join(problem),
                "root_cause": root_cause,
            })

    return bad_cases


# ============================================================
# 报告生成
# ============================================================

def print_report(baseline, ab_full, ab_rewrite, ab_judge, ab_rerank, bad_cases):
    """打印评估报告"""
    print("\n\n")
    print("=" * 60)
    print("  XINZHIDAO - Retrieval Quality Evaluation Report")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Test Cases: {len(baseline)}")
    print("=" * 60)

    # Baseline metrics
    avg_faith = sum(r["faithfulness"] for r in baseline) / len(baseline)
    avg_relev = sum(r["relevancy"] for r in baseline) / len(baseline)
    avg_compl = sum(r["completeness"] for r in baseline) / len(baseline)
    hit_count = sum(1 for r in baseline if r["hit"])
    hit_rate = hit_count / len(baseline) * 100
    avg_time = sum(r["time"] for r in baseline) / len(baseline)

    print(f"\n--- Baseline (Full Pipeline, 20 cases) ---")
    print(f"    Faithfulness:      {avg_faith:.2f}")
    print(f"    Answer Relevancy:  {avg_relev:.2f}")
    print(f"    Completeness:      {avg_compl:.2f}")
    print(f"    Retrieval HitRate: {hit_rate:.0f}% ({hit_count}/20)")
    print(f"    Avg Response Time: {avg_time:.1f}s")

    # By query type
    print(f"\n--- By Query Type ---")
    for qtype in ["精确查询", "模糊概念", "复合查询", "口语化查询"]:
        group = [r for r in baseline if r["type"] == qtype]
        if group:
            avg_f = sum(r["faithfulness"] for r in group) / len(group)
            avg_r = sum(r["relevancy"] for r in group) / len(group)
            hits = sum(1 for r in group if r["hit"])
            print(f"    {qtype} ({len(group)} cases): Faith={avg_f:.2f} Relev={avg_r:.2f} HitRate={hits}/{len(group)}")

    # A/B Summary
    print(f"\n--- A/B Comparison Summary ---")
    print(f"    Full Hybrid vs Semantic-only:  {ab_full[0]}/20 vs {ab_full[1]}/20")
    print(f"    With Rewrite vs No Rewrite:    {ab_rewrite[0]}/20 vs {ab_rewrite[1]}/20")
    print(f"    With AI Judge vs No Judge:     {ab_judge[0]}/20 vs {ab_judge[1]}/20")
    print(f"    With Rerank vs No Rerank:      {ab_rerank[0]}/20 vs {ab_rerank[1]}/20")

    # Bad Cases
    print(f"\n--- Bad Cases: {len(bad_cases)} ---")
    for bc in bad_cases:
        print(f"    [{bc['id']}] {bc['question']}")
        print(f"         Problem: {bc['problem']} | RootCause: {bc['root_cause']}")

    # Resume-ready data
    print(f"\n\n{'='*60}")
    print(f"  RESUME DATA (ready to use)")
    print(f"{'='*60}")
    print(f"  Avg Faithfulness: {avg_faith:.2f}")
    print(f"  Avg Relevancy: {avg_relev:.2f}")
    print(f"  Retrieval HitRate: {hit_rate:.0f}%")
    print(f"  Test Cases: 20 (4 types)")
    print(f"  Bad Cases: {len(bad_cases)}")

    # Save results
    output = {
        "eval_time": datetime.now().isoformat(),
        "test_case_count": len(baseline),
        "summary": {
            "avg_faithfulness": round(avg_faith, 2),
            "avg_relevancy": round(avg_relev, 2),
            "avg_completeness": round(avg_compl, 2),
            "hit_rate": f"{hit_rate:.0f}%",
            "avg_time_seconds": round(avg_time, 1),
        },
        "ab_comparisons": {
            "full_vs_semantic": {"full": ab_full[0], "semantic": ab_full[1]},
            "rewrite_vs_no_rewrite": {"with_rewrite": ab_rewrite[0], "without_rewrite": ab_rewrite[1]},
            "judge_vs_no_judge": {"with_judge": ab_judge[0], "without_judge": ab_judge[1]},
            "rerank_vs_no_rerank": {"with_rerank": ab_rerank[0], "without_rerank": ab_rerank[1]},
        },
        "bad_cases": bad_cases,
    }

    output_file = Path(__file__).parent / "eval_results_full.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved: {output_file}")

    badcase_file = Path(__file__).parent / "bad_cases.json"
    with open(badcase_file, "w", encoding="utf-8") as f:
        json.dump(bad_cases, f, ensure_ascii=False, indent=2)
    print(f"  Bad Cases saved: {badcase_file} ({len(bad_cases)} cases)")

    return output


# ============================================================
# Main
# ============================================================

async def main():
    print("=" * 60)
    print("  XinzhiDao - Retrieval Quality Evaluation")
    print(f"  Test Cases: {len(TEST_CASES)}")
    print(f"  KB Documents: test_product.txt, graduation guide, etc.")
    print("=" * 60)

    # 1. Baseline
    baseline = await run_baseline()

    # 2. A/B Comparisons
    ab_full = run_ab_full_vs_simple()
    ab_rewrite = run_ab_rewrite_vs_no_rewrite()
    ab_judge = run_ab_judge_vs_no_judge()
    ab_rerank = run_ab_rerank_vs_no_rerank()

    # 3. Bad Cases
    bad_cases = collect_bad_cases(baseline)

    # 4. Report
    report = print_report(baseline, ab_full, ab_rewrite, ab_judge, ab_rerank, bad_cases)
    return report


if __name__ == "__main__":
    asyncio.run(main())
