import os
import sys
import json
import difflib
from textwrap import dedent

# Add project root to path so we can import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_google_genai import ChatGoogleGenerativeAI
from tools.rag_tool import policy_search_tool
import config

def calculate_overlap_score(expected: str, generated: str) -> float:
    """
    Deterministic metric: calculates word overlap ratio between expected and generated text.
    Similar to a ROUGE-1 score.
    """
    matcher = difflib.SequenceMatcher(None, expected.lower().split(), generated.lower().split())
    return matcher.ratio()

def get_llm_judge():
    return ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.0 # Deterministic as possible
    )

def evaluate_generation(dataset_path: str):
    print(f"--- Starting Generation Evaluation (LLM-as-a-Judge) ---")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    llm = get_llm_judge()
    
    total_questions = len(dataset)
    total_overlap = 0.0
    total_relevance = 0.0
    
    print(f"Loaded {total_questions} test cases for generation eval.\n")
    
    for i, test_case in enumerate(dataset):
        question = test_case["question"]
        expected_answer = test_case["expected_answer"]
        
        print(f"Q{i+1}: {question}")
        
        # 1. GENERATE THE ANSWER
        # We will use the agent LLM to answer it based on the RAG context.
        context = policy_search_tool.invoke({"query": question})
        
        prompt = dedent(f"""
        You are a helpful AI assistant. Answer the user's question based strictly on the provided context.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer concisely:
        """).strip()
        
        response = llm.invoke(prompt)
        generated_answer = response.content.strip()
        
        print(f"  Expected: {expected_answer}")
        print(f"  Generated: {generated_answer}")
        
        # 2. DETERMINISTIC METRIC (Word Overlap / ROUGE equivalent)
        overlap_score = calculate_overlap_score(expected_answer, generated_answer)
        total_overlap += overlap_score
        print(f"  [Metric] Word Overlap Score: {overlap_score:.2f}")
        
        # 3. SEMANTIC METRIC (LLM-as-a-Judge)
        # We ask a strict judge prompt to rate the answer from 1 to 5
        judge_prompt = dedent(f"""
        You are an impartial judge. Your task is to evaluate the quality of a generated answer compared to an expected answer.
        
        Question: {question}
        Expected Answer: {expected_answer}
        Generated Answer: {generated_answer}
        
        Rate the generated answer's relevance and correctness from 1 to 5, where:
        1 = Completely incorrect or irrelevant
        5 = Perfectly captures the meaning of the expected answer (even if words differ)
        
        Respond with ONLY the integer number.
        """).strip()
        
        try:
            judge_response = llm.invoke(judge_prompt).content.strip()
            score = float(judge_response) / 5.0 # Normalize to 0-1
        except Exception as e:
            print(f"  [Error] Judge failed to parse score, defaulting to 0. {e}")
            score = 0.0
            
        total_relevance += score
        print(f"  [Metric] LLM Judge Relevance: {score:.2f}\n")

    avg_overlap = total_overlap / total_questions
    avg_relevance = total_relevance / total_questions
    
    print(f"--- Generation Evaluation Complete ---")
    print(f"Average Deterministic Overlap: {avg_overlap:.2f}")
    print(f"Average LLM Judge Relevance: {avg_relevance:.2f}")
    
    return avg_overlap, avg_relevance

if __name__ == "__main__":
    dataset_file = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    evaluate_generation(dataset_file)
