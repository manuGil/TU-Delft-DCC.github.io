"""
A runner for evaluation the perfomance of the assistant
"""

import json
from pathlib import Path
from guia.indexer import QuartoIndexer
from guia.evaluation.test_dataset import TestDataset, create_sample_dataset
from guia.evaluation.retrieval_metrics import RetrievalEvaluator
from guia.evaluation.e2e_evaluation import EndToEndEvaluator
from guia.evaluation.perfomance_monitor import PerfomanceMonitor
import argparse
import sys

def run_full_evaluation(
        indexer: QuartoIndexer,
        test_dataset : TestDataset, 
        output_dir: str = './evaluation_results',
        anthropic_api_key: str | None = None
):
    """ Run complete evaluation suite"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("=" * 60)
    print("RUNNING EVALUATION SUITE")
    print("=" * 60)

    # 1. Retrieval evaluation
    print('\n1. Evaluation retrieval quality...')
    retrieval_eval = RetrievalEvaluator(indexer)
    retrieval_results = retrieval_eval.evaluate_dataset(test_dataset, k_values=[1,3,5])

    # Save retrieval results
    with open(output_path / "retrieval_metrics.json", "w") as f:
        json.dump(retrieval_results, f, indent=2)

    # Print summary
    agg = retrieval_results['aggregated_metrics']
    print(f"\nRetrieval Metrics (averaged across {len(test_dataset.test_cases)} queries):")
    print(f"  Precision@3: {agg['precision@3']['mean']:.3f} ± {agg['precision@3']['std']:.3f}")
    print(f"  Recall@3:    {agg['recall@3']['mean']:.3f} ± {agg['recall@3']['std']:.3f}")
    print(f"  NDCG@3:      {agg['ndcg@3']['mean']:.3f} ± {agg['ndcg@3']['std']:.3f}")
    print(f"  MRR:         {agg['mrr']['mean']:.3f} ± {agg['mrr']['std']:.3f}")

    # 2. End-to-End evaluation
    e2e_results = None  # Initialize to avoid unbound variable
    if anthropic_api_key:
        print("\n2. Evaluating end-to-end answer quality...")
        e2e_eval = EndToEndEvaluator(indexer, anthropic_api_key)

        e2e_results = []
        for test_case in test_dataset.test_cases:
            print(f"  Processing: {test_case['question'][:60]}...")

            # Get RAG answer
            rag_result = e2e_eval.get_rag_answer(test_case['question'])

            # Keyword evaluation
            keyword_eval = e2e_eval.evaluate_answer_quality(
                test_case['question'],
                rag_result['answer'],
                test_case.get('expected_keywords', [])
            )

            # LLM judge evaluation
            llm_judge = e2e_eval.llm_judge_evaluation(
                test_case['question'],
                rag_result['answer'],
                rag_result['context']
            )

            e2e_results.append({
                'question': test_case['question'],
                'category': test_case['category'],
                'answer': rag_result['answer'],
                'keyword_evaluation': keyword_eval,
                'llm_judge': llm_judge,
                'retrieved_chunks': rag_result['retrieved_chunks']
            })

        # save E2eE results
        with open(output_path / "e2e_evaluation.json", "w") as f:
            json.dump(e2e_results, f, indent=2)

        # Print summary
        avg_keyword_coverage = sum(r['keyword_evaluation']['keyword_coverage'] 
                                    for r in e2e_results) / len(e2e_results)
        avg_llm_score = sum(r['llm_judge'].get('overall', 0) 
                            for r in e2e_results) / len(e2e_results)
        
        print(f"\nEnd-to-End Metrics:")
        print(f"  Keyword Coverage: {avg_keyword_coverage:.2%}")
        print(f"  LLM Judge Score:  {avg_llm_score:.2f}/5.0")
    else:
        print("\n2. Skipping E2E evaluation (no API key provided)")

    # 3. Performance analysis
    print("\n3. Analysis retrieval performance...")
    monitor = PerfomanceMonitor()
    # Measure search performance
    monitored_search = monitor.measure_perfomance(indexer.search)

    for test_case in test_dataset.test_cases:
        monitored_search(test_case['question'], n_results=5)
    perf_stats = monitor.get_statistics()
    monitor.save_metrics(output_path / "performance_metrics.json")
    
    print(f"\nPerformance Metrics ({perf_stats['total_calls']} queries):")
    print(f"  Avg Latency: {perf_stats['latency']['mean']*1000:.1f}ms")
    print(f"  P95 Latency: {perf_stats['latency']['p95']*1000:.1f}ms")
    print(f"  Max Latency: {perf_stats['latency']['max']*1000:.1f}ms")

    # 4. Generate HTML Report
    print("\n4. Generating evaluation report...")
    generate_html_report(output_path, retrieval_results, e2e_results if anthropic_api_key else None, perf_stats)
    
    print(f"\n✓ Evaluation complete! Results saved to: {output_path}")
    print(f"  - retrieval_metrics.json")
    if anthropic_api_key:
        print(f"  - e2e_evaluation.json")
    print(f"  - performance_metrics.json")
    print(f"  - evaluation_report.html")

def generate_html_report(output_path, retrieval_results, e2e_results, perf_stats):
    """Generate HTML report"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .metric {{ background-color: #f9f9f9; }}
        .good {{ color: green; }}
        .medium {{ color: orange; }}
        .poor {{ color: red; }}
    </style>
</head>
<body>
    <h1>RAG System Evaluation Report</h1>
    
    <h2>1. Retrieval Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Mean</th>
            <th>Std Dev</th>
            <th>Min</th>
            <th>Max</th>
        </tr>
"""
    
    agg = retrieval_results['aggregated_metrics']
    for metric in ['precision@3', 'recall@3', 'ndcg@3', 'mrr']:
        values = agg[metric]
        html += f"""
        <tr>
            <td>{metric}</td>
            <td>{values['mean']:.3f}</td>
            <td>{values['std']:.3f}</td>
            <td>{values['min']:.3f}</td>
            <td>{values['max']:.3f}</td>
        </tr>
"""
    html += """
    </table>
    
    <h2>2. Performance Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
"""
    
    html += f"""
        <tr><td>Total Queries</td><td>{perf_stats['total_calls']}</td></tr>
        <tr><td>Avg Latency</td><td>{perf_stats['latency']['mean']*1000:.1f}ms</td></tr>
        <tr><td>P95 Latency</td><td>{perf_stats['latency']['p95']*1000:.1f}ms</td></tr>
        <tr><td>Max Latency</td><td>{perf_stats['latency']['max']*1000:.1f}ms</td></tr>
    </table>
"""

    
    if e2e_results:
        html += """
    <h2>3. Answer Quality</h2>
    <table>
        <tr>
            <th>Question</th>
            <th>Keyword Coverage</th>
            <th>LLM Judge Score</th>
        </tr>
"""
        for result in e2e_results:
            coverage = result['keyword_evaluation']['keyword_coverage']
            llm_score = result['llm_judge'].get('overall', 0)
            html += f"""
        <tr>
            <td>{result['question'][:80]}...</td>
            <td>{coverage:.1%}</td>
            <td>{llm_score:.1f}/5.0</td>
        </tr>
"""
    
    html += """
    </table>
</body>
</html>
"""

    
    with open(output_path / "evaluation_report.html", 'w') as f:
        f.write(html)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate RAG System')
    parser.add_argument('--test-data', default='test_dataset.json', help='Path to test dataset')
    parser.add_argument('--output-dir', default='./evaluation_results', help='Output directory')
    parser.add_argument('--api-key', help='Anthropic API key for E2E evaluation')
    parser.add_argument('--create-sample', action='store_true', help='Create sample test dataset')

    args = parser.parse_args()

    if args.create_sample:
        print("Creating sample test dataset")
        create_sample_dataset()
        print("Sample dataset saved to test_dataset.json")
    
    # Load indexer
    # Add script directory to path for imports
    SCRIPT_DIR = Path(__file__).parent.resolve()
    sys.path.insert(0, str(SCRIPT_DIR))

    # initialize indexer with path relative to script location
    CHROMA_PATH = SCRIPT_DIR.parent / "chroma_db"
    print(f"CHROMA DIR: {CHROMA_PATH}")
    indexer = QuartoIndexer(persist_directory=str(CHROMA_PATH))

    # Load test dataset
    dataset = TestDataset.load(args.test_data)
    print(f"Loaded {len(dataset.test_cases)} test cases")

    # Run evaluation
    run_full_evaluation(indexer, dataset, args.output_dir, args.api_key)
