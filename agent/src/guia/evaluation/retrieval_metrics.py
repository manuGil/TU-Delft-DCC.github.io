from typing import List, Dict, Set
import numpy as np
from guia.indexer import QuartoIndexer
from guia.evaluation.test_dataset import TestDataset

class RetrievalEvaluator:
    def __init__(self, indexer: QuartoIndexer):
        self.indexer = indexer

    def precision_at_k(self, retrieved: List[str],
                       relevant: List[str], k:int) -> float:
        """
        Precision@K: What fraction of retrieved docs (top-k) are relevant?
        """
        retrieved_k = set(retrieved[:k])
        relevant_set = set(relevant)

        if not retrieved_k:
            return 0.0
        
        return len(retrieved_k & relevant_set) / len(retrieved_k)

    def recall_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Recall@K: What fraction of relevant docs are in top-k retrieved?
        """
        retrieved_k = set(retrieved[:k])
        relevant_set = set(relevant)

        if not relevant_set:
            return 0.0
        
        return len(retrieved_k & relevant_set) / len(relevant_set)
    
    def mean_reciprocal_rank(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        MMR: 1/rank of first relvant document
        """

        relevant_set = set(relevant)

        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0/i 
        
        return 0.0
    
    def ndcg_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Normalized Discounted Commulative Gain@K
        Measures ranking quality with position discount
        """

        def dcg(relevances: List[int], k:int) -> float:
            relevances = relevances[:k]
            return sum(rel / np.log2(i +2) for i, rel in enumerate(relevances))
        
        # binary relevance: 1 if in relevant set, 0 otherwise
        relevant_set = set(relevant)
        retrieved_relevances = [1 if doc in relevant_set else 0 
                                for doc in retrieved[:k]]

        # Ideal ranking (all relevant docs firts)
        ideal_relevances = [1] * min(len(relevant), k) + [0] * max(0, k - len(relevant)))

        dcg_val = dcg(retrieved_relevances, k)
        idcg_val = dcg(ideal_relevances, k)

        if idcg_val == 0:
            return 0.0
        
        return dcg_val / idcg_val
    
    def evaluate_query(self, query: str, expeced_chunks: List[str], 
                       k_values: List[int] = [1,3,5]) -> Dict:
        """
        Evaluate a single query accross multiple metrics
        """
        # Get retrieval results
        results = self.indexer.search(query, n_results=max(k_values))

        # Extract chunk Ids from metadata
        retrieved_ids = [meta.get('chunk_id', meta.get('file', ''))
                         for meta in results['metadatas'][0]]
        
        metrics = {
            'query': query,
            'retrieved': len(retrieved_ids),
            'expected_count': len(expeced_chunks)
        }

        # Calculate metrics at different k values
        for k in k_values:
            metrics[f'precision@{k}'] = self.precision_at_k(retrieved_ids, expeced_chunks, k)
            metrics[f'recall@{k}'] = self.recall_at_k(retrieved_ids, expeced_chunks, k)
            metrics[f'ndcg@{k}'] = self.ndcg_at_k(retrieved_ids, expeced_chunks, k)

        metrics['mrr'] = self.mean_reciprocal_rank(retrieved_ids, expeced_chunks)

        # Add retrieved Ids for debugging
        metrics['retrieved_ids'] = retrieved_ids[:max(k_values)]
        metrics['expected_ids'] = expeced_chunks

        return metrics
    
    def evaluate_dataset(self, dataset: TestDataset,
                         k_values: List[int] = [1,2,3]) -> Dict:
        """
        Evaluate entire test dataset
        """

        all_results = []

        for test_case in dataset.test_cases:
            result = self.evaluate_query(
                test_case['question'],
                test_case['expected_chunks'],
                k_values
            )
            result['category'] = test_case['category']
            all_results.append(result)

        # aggregate metrics
        aggregated = self._aggregated_metrics(all_results, k_values)

        return {
            'individual_results': all_results,
            'aggregated_metrics': aggregated
        }
    
    def _aggregated_metrics(self, results: List[Dict], k_values: List[int]) -> Dict:
        """ 
        Calculate average metrics across all queries
        """
        aggregated = {}

        metric_names =   [f'precision@{k}' for k in k_values] + \
                        [f'recall@{k}' for k in k_values] + \
                        [f'ndcg@{k}' for k in k_values] + \
                        ['mrr']
        
        for metric_name in metric_names:
            values = [r[metric_name] for r in results if metric_name in r]
            aggregated[metric_name] = {
                'mean': np.mean(values) if values else 0.0,
                'std': np.std(values) if values else 0.0,
                'min': np.min(values) if values else 0.0,
                'max': np.max(values) if values else 0.0,
            }

        # category breakdown
        categories = set(r['category'] for r in results)
        aggregated['by_category'] = {}

        for category in categories:
            cat_results = [r for r in results if r['category'] == category]
            aggregated['by_category'][category] = {
                metric: np.mean([r[metric] for r in cat_results])
                for metric in metric_names
            }
        
        return aggregated

