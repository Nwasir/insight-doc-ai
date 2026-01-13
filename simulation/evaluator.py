import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def run_evaluation():
    print("⚖️  Judge Agent Initialized. Grading responses...")
    
    # 1. Load the Simulation Report
    try:
        with open("simulation/report.json", "r") as f:
            report_data = json.load(f)
    except FileNotFoundError:
        print("❌ Report not found. Run sim_agent.py first.")
        return

    # 2. Initialize the Judge (Gemini)
    judge_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=GOOGLE_API_KEY
    )

    score = 0
    total = len(report_data)
    
    print(f"\n📝 Grading {total} Test Cases...\n")
    print(f"{'ID':<5} | {'Result':<10} | {'Latency':<10} | {'Reason'}")
    print("-" * 80)

    for i, item in enumerate(report_data):
        question = item['question']
        agent_ans = item['agent_answer']
        expected_ans = item['expected']
        
        # 3. Create Grading Prompt
        # We ask the AI to be an objective judge.
        grading_prompt = f"""
        You are a strict technical grader. Compare the ACTUAL ANSWER with the EXPECTED ANSWER.
        
        Question: {question}
        
        EXPECTED ANSWER: {expected_ans}
        
        ACTUAL ANSWER: {agent_ans}
        
        Rule:
        - If the ACTUAL answer contains the core correct information from the EXPECTED answer, grade it PASS.
        - If it is wrong, missing key numbers, or says "Data Not Found" when it shouldn't, grade it FAIL.
        - Output ONLY the word "PASS" or "FAIL" followed by a very short reason.
        
        Format: PASS - Reason... OR FAIL - Reason...
        """
        
        try:
            # Ask the Judge
            grade_response = judge_llm.invoke(grading_prompt).content.strip()
            
            # Parse Result
            status = "PASS" if "PASS" in grade_response.upper() else "FAIL"
            if status == "PASS":
                score += 1
            
            # Print row
            print(f"{i+1:<5} | {status:<10} | {item['latency']}s      | {grade_response.replace('PASS - ', '').replace('FAIL - ', '')[:50]}...")
            
        except Exception as e:
            print(f"{i+1:<5} | ERROR      | -           | {e}")

    # 4. Final Score
    accuracy = (score / total) * 100
    print("-" * 80)
    print(f"\n🎯 Final Accuracy Score: {accuracy}% ({score}/{total})\n")

if __name__ == "__main__":
    run_evaluation()