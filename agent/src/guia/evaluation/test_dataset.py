"""
A test dataset for the evaluation framework of Guia
"""
from typing import List, Dict
import json

class TestDataset:
    """Creates and manages test quetions with expected answers"""

    def __init__(self):
        self.test_cases =[]
    
    def add_test_case(self, question: str, expected_chunks: List[str],
                      expected_answer_keywords: List[str] = None,
                      category: str = "general"):
        """
        Add a test case

        Args:
            question: the test question
            expected_chunks: list of chunks_ids that should be retrieved
            expected_answers_keywords: keywords that should appear in the answer
            category: category for analysis (e.g., 'installation', 'configuation')
        """

        self.test_cases.append({
            'question': question,
            'expected_chunks': expected_chunks,
            'expected_answer_keywords': expected_answer_keywords or [],
            'category': category
        })

    def save(self, filepath: str):
        """Save test dataset to JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.test_cases, f, indent=2)


    @classmethod
    def load(cls, filepath: str):
        """Load test dataset from JSON"""

        dataset = cls()
        with open(filepath, 'r') as f:
            dataset.test_cases = json.load(f)
        return dataset
    
# Create sample test cases
def create_sample_dataset():
    dataset = TestDataset()

    # Define test cases
    dataset.add_test_case(
        question="How do I renew SSL certificates?",
        expected_chunks=['infrastructure_ssl_certificates_6', 
                         'infrastructure_ssl_certificates_0', 
                         'infrastructure_ssl_certificates_3'],
        expected_answer_keywords=["SSL/TSL", "renew", "HARICA", "certificate"],
        category="certificates"
    )

    # TODO: add more test cases

    dataset.save("test_dataset.json")
    return dataset

if __name__ == '__main__':
    create_sample_dataset()

