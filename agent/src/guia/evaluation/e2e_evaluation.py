"""
Evaluates the complete RAG pipeline including answer quality
"""

import json 
import anthropic
from typing import Dict, List
from guia.indexer import QuartoIndexer

class EndToEndEvaluator:
    def __init__(self, indexer: QuartoIndexer, anthropic_api_key: str = None):
        self.indexer = indexer
        if anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        else:
            self.client = None

    def get_rag_answer(self, question:str, n_results: int = 3) -> Dict:
        """
        Get answer using RAG pipeline
        """

        # Retrieved documents
        results = self.indexer.search(question, n_results=n_results)

        # Format context
        context_parts = []
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            context_parts.append(
                f"[{metadata['file']} - {metadata['section_header']}]\n{doc}"
            )
        
        context = "\n\n---\n\n".join(context_parts)

        # Generate answer (if API key provided)
        answer = None
        if self.client:
            prompt = f"""Based on the following documentation, answer the question: {question}

Documentation:
{context}

Please provide a clear, consise answer bassed only on the information provided.
"""
            response = self.client.messages.create(
                model = "claude-sonnet-4-20250514",
                max_tokens =1000,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.content[0].text

        return {
            'question': question,
            'context': context,
            'answer': answer,
            'retrieved_chunks': [
                {
                    'file': m['file'],
                    'section': m['section_header'],
                    'content_preview': d[:200] + '...'
                }
                for d, m in zip(results['documents'][0], results['metadatas'][0])
            ]
        }

    def evaluate_answer_quality(self, question: str, answer: str,
                                expected_keyworkds: List[str]) -> Dict:
        """
        Simple keyword-based answer quality check
        """
        answer_lower = answer.lower()

        keyword_found = [kw for kw in expected_keyworkds if kw.lower() in answer_lower]

        return{
            'keyword_coverage': len(keyword_found) / len(expected_keyworkds) if expected_keyworkds else 1.0,
            'keword_found': keyword_found,
            'keword_missing': [kw for kw in expected_keyworkds if kw not in keyword_found],
            'answer_length': len(answer)
        }

    def llm_judge_evaluation(self, question: str, answer: str, context: str) -> Dict:
        """
        Use LLM as a judge to evaluate answer quality.
        """
        # TODO: is this a good idea?

        if not self.client:
            return {'error': 'No API key provided'}
        
        judge_prompt = f"""You are evaluating the quality of an AI assistant's answer.
Question: {question}

Context provided to assistant:
{context}

Assistant's answer:
{answer}

Please evaluate the answer on these creteria (score 1-5 for each):
1. Correcteness: Is the answer factually correct based on the context?
2. Completeness: Does it fully address the question?
3. Relevance: Does it stay focused on the question?
4. Clarity: Is it well-written and easy to understand?
5. Groundness: Is is based only on the provided context (no hallucinations)?

Responde in JSON format:
{{
    "correctness": <score>,
    "completeness": <score>,
    "relevance": <score>,
    "clarity": <score>,
    "groundness": <score>,
    "explanation": <brief explanation>,
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": judge_prompt}]
        )

        try:
            # Extract JSON from response
            response_text = response.content[0].text
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*}', response_text, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
                return evaluation
            else:
                return {'error': 'Could not parse JSON', 'raw': response_text}
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON response', 'raw': response_text}