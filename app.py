import streamlit as st
import json
import os
from datetime import datetime
import uuid

# Page config
st.set_page_config(
    page_title="Agent or Workflow? The Great AI Debate",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for ZenML styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #7C3AED 0%, #A855F7 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .quiz-container {
        background: #f8fafc;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    .code-block {
        background: #1e293b;
        color: #e2e8f0;
        padding: 1.5rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        margin: 1rem 0;
    }
    .vote-button {
        background: #7C3AED;
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 8px;
        font-size: 1.2rem;
        margin: 0.5rem;
        cursor: pointer;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem;
        background: linear-gradient(90deg, #7C3AED 0%, #A855F7 100%);
        color: white;
        border-radius: 10px;
    }
    .zenml-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Quiz data
QUIZ_DATA = [
    {
        "title": "Prompt Chaining",
        "code": '''def generate_content(topic):
    # Step 1: Generate initial joke
    joke = llm.call(f"Write a joke about {topic}")
    
    # Step 2: Check quality (predefined gate)
    if has_punchline(joke):
        return joke
    
    # Step 3: Improve the joke
    better_joke = llm.call(f"Make this funnier: {joke}")
    
    # Step 4: Final polish
    final_joke = llm.call(f"Add a twist: {better_joke}")
    
    return final_joke''',
        "correct": "Workflow",
        "explanation": "This follows a predefined sequence of steps with programmatic gates. The control flow is fixed by the code."
    },
    {
        "title": "Tool-Calling Agent",
        "code": '''def solve_math_problem(question):
    messages = [question]
    
    while True:
        # LLM decides what to do next
        response = llm.call(messages)
        
        if response.wants_tool():
            # LLM chose to use a tool
            tool_result = execute_tool(response.tool, response.args)
            messages.append(tool_result)
        else:
            # LLM decided it's done
            return response.answer''',
        "correct": "Agent",
        "explanation": "The LLM controls its own execution flow based on environmental feedback. It decides when to use tools and when to stop."
    },
    {
        "title": "Routing",
        "code": '''def handle_request(user_input):
    # Classify the input
    category = llm.call(f"Classify this as 'story', 'joke', or 'poem': {user_input}")
    
    # Route to predefined handlers
    if category == "story":
        return write_story(user_input)
    elif category == "joke":
        return write_joke(user_input)
    elif category == "poem":
        return write_poem(user_input)''',
        "correct": "Workflow",
        "explanation": "Despite using an LLM for classification, this follows predefined routing logic. The control flow is determined by code structure."
    },
    {
        "title": "Parallelization",
        "code": '''def create_content_pack(topic):
    # Launch multiple LLM calls simultaneously
    story_task = async_llm_call(f"Write a story about {topic}")
    joke_task = async_llm_call(f"Write a joke about {topic}")
    poem_task = async_llm_call(f"Write a poem about {topic}")
    
    # Wait for all to complete
    story = await story_task
    joke = await joke_task
    poem = await poem_task
    
    # Combine results
    return combine(story, joke, poem)''',
        "correct": "Workflow",
        "explanation": "Multiple predefined tasks execute in parallel. The structure and sequence are fixed by the programmer."
    },
    {
        "title": "Orchestrator-Worker",
        "code": '''def create_report(topic):
    # Central planner breaks down the task
    sections = planner_llm.call(f"Plan sections for report on {topic}")
    
    # Delegate each section to worker LLMs
    completed_sections = []
    for section in sections:
        content = worker_llm.call(f"Write section: {section}")
        completed_sections.append(content)
    
    # Synthesize final report
    return synthesize(completed_sections)''',
        "correct": "Workflow",
        "explanation": "Despite dynamic planning, this follows a fixed pattern: Plan → Execute → Synthesize. The LLM fills parameters within predetermined control structures."
    },
    {
        "title": "Research Agent",
        "code": '''def research_question(query):
    findings = []
    
    while not satisfied_with_research(findings):
        # Agent decides what to research next
        next_action = llm.call(f"Given {findings}, what should I research next for: {query}")
        
        if next_action.type == "search":
            result = web_search(next_action.query)
            findings.append(result)
        elif next_action.type == "analyze":
            analysis = llm.call(f"Analyze: {next_action.data}")
            findings.append(analysis)
        elif next_action.type == "done":
            break
    
    return compile_research(findings)''',
        "correct": "Agent",
        "explanation": "The LLM controls its own execution flow, deciding what to research next based on accumulated context and environmental feedback."
    },
    {
        "title": "Evaluator-Optimizer",
        "code": '''def improve_content(topic):
    content = llm.call(f"Write content about {topic}")
    
    for attempt in range(max_iterations):
        # Evaluate current content
        feedback = evaluator_llm.call(f"Grade this content: {content}")
        
        if feedback.grade == "good":
            break
            
        # Improve based on feedback
        content = llm.call(f"Improve this content: {content}. Feedback: {feedback}")
    
    return content''',
        "correct": "Workflow",
        "explanation": "This follows a structured feedback loop with predefined evaluation criteria. The control flow is managed by the code structure."
    }
]

# Initialize session state
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []
if 'quiz_completed' not in st.session_state:
    st.session_state.quiz_completed = False
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Simple file-based storage (will be replaced with Google Sheets)
def save_vote(question_num, user_vote, correct_answer):
    vote_data = {
        'session_id': st.session_state.session_id,
        'question_num': question_num,
        'user_vote': user_vote,
        'correct_answer': correct_answer,
        'timestamp': datetime.now().isoformat()
    }
    
    # Try to read existing data
    try:
        if os.path.exists('quiz_votes.json'):
            with open('quiz_votes.json', 'r') as f:
                data = json.load(f)
        else:
            data = []
    except:
        data = []
    
    data.append(vote_data)
    
    # Save back
    try:
        with open('quiz_votes.json', 'w') as f:
            json.dump(data, f)
    except:
        pass  # Fail silently if can't save

def get_stats():
    try:
        if os.path.exists('quiz_votes.json'):
            with open('quiz_votes.json', 'r') as f:
                data = json.load(f)
            return data
        return []
    except:
        return []

# Main app
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Agent or Workflow?</h1>
        <h3>The Great AI Debate</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.quiz_started:
        # Landing page
        st.markdown("""
        ### Everyone wants to build "AI agents" but nobody really knows what they are.
        
        This quiz collects the public's understanding of this fundamental distinction.
        
        **What's the difference?**
        - **Workflow**: LLMs and tools orchestrated through predefined code paths
        - **Agent**: LLM dynamically directs its own processes and tool usage
        
        📖 **Recommended reading:** [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) by Anthropic
        
        Ready to test your intuition? Let's see how you compare to the crowd...
        """)
        
        if st.button("🚀 START QUIZ", type="primary"):
            st.session_state.quiz_started = True
            st.rerun()
    
    elif not st.session_state.quiz_completed:
        # Quiz in progress
        current_q = st.session_state.current_question
        question_data = QUIZ_DATA[current_q]
        
        st.markdown(f"### Question {current_q + 1} of {len(QUIZ_DATA)}")
        st.markdown(f"**{question_data['title']}**")
        
        # Code block
        st.code(question_data['code'], language='python')
        
        st.markdown("### Is this an Agent or Workflow?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 AGENT", type="primary", use_container_width=True):
                st.session_state.user_answers.append("Agent")
                save_vote(current_q, "Agent", question_data['correct'])
                show_result(question_data, "Agent")
        
        with col2:
            if st.button("⚙️ WORKFLOW", type="secondary", use_container_width=True):
                st.session_state.user_answers.append("Workflow")
                save_vote(current_q, "Workflow", question_data['correct'])
                show_result(question_data, "Workflow")
    
    else:
        # Quiz completed - show results
        show_final_results()

def show_result(question_data, user_answer):
    correct = question_data['correct']
    is_correct = user_answer == correct
    
    if is_correct:
        st.success(f"✅ Correct! This is a **{correct}**")
    else:
        st.error(f"❌ Not quite. This is actually a **{correct}**")
    
    st.info(f"**Explanation:** {question_data['explanation']}")
    
    if st.button("Next Question →"):
        if st.session_state.current_question < len(QUIZ_DATA) - 1:
            st.session_state.current_question += 1
        else:
            st.session_state.quiz_completed = True
        st.rerun()

def show_final_results():
    st.markdown("## 🎉 Quiz Complete!")
    
    # Calculate score
    correct_count = 0
    for i, user_answer in enumerate(st.session_state.user_answers):
        if user_answer == QUIZ_DATA[i]['correct']:
            correct_count += 1
    
    score_pct = (correct_count / len(QUIZ_DATA)) * 100
    
    st.markdown(f"### Your Score: {correct_count}/{len(QUIZ_DATA)} ({score_pct:.0f}%)")
    
    if score_pct >= 80:
        st.success("🏆 Agent Expert! You really understand the distinction!")
    elif score_pct >= 60:
        st.info("🎯 Pretty good! You're getting the hang of it.")
    else:
        st.warning("🤔 Keep studying! The agent/workflow distinction is tricky.")
    
    # Show crowd stats (if available)
    stats = get_stats()
    if stats:
        st.markdown("### 📊 How You Compare to the Crowd")
        
        for i, question_data in enumerate(QUIZ_DATA):
            question_votes = [v for v in stats if v['question_num'] == i]
            if question_votes:
                agent_votes = len([v for v in question_votes if v['user_vote'] == 'Agent'])
                total_votes = len(question_votes)
                agent_pct = (agent_votes / total_votes) * 100 if total_votes > 0 else 0
                
                correct_answer = question_data['correct']
                user_answer = st.session_state.user_answers[i]
                is_correct = user_answer == correct_answer
                
                status = "✅" if is_correct else "❌"
                st.markdown(f"**{status} {question_data['title']}**: {agent_pct:.0f}% said Agent, {100-agent_pct:.0f}% said Workflow (Answer: {correct_answer})")
    
    if st.button("🔄 Take Quiz Again"):
        # Reset quiz
        st.session_state.quiz_started = False
        st.session_state.current_question = 0
        st.session_state.user_answers = []
        st.session_state.quiz_completed = False
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Footer
st.markdown("""
<div class="footer">
    <div class="zenml-logo">
        <span>🧘‍♂️</span>
        <div>
            <strong>Brought to you by ZenML Team</strong><br>
            <a href="https://github.com/zenml-io/zenml" style="color: white;">⭐ GitHub</a> | 
            <a href="https://zenml.io" style="color: white;">🌐 zenml.io</a>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()