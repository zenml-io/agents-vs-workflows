import streamlit as st
import json
import os
from datetime import datetime
import uuid
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import threading

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

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
        background: #64748b;
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

def ensure_headers(worksheet):
    headers = ['Session ID', 'Question Number', 'User Vote', 'Correct Answer', 'Timestamp']
    existing = worksheet.row_values(1)
    if existing != headers:
        worksheet.insert_row(headers, 1)

def save_vote_threaded(question_num, user_vote, correct_answer, session_id, secrets):
    """
    A thread-safe function to save a vote. It creates its own gspread client
    and is designed to be run in a background thread.
    """
    try:
        credentials = Credentials.from_service_account_info(
            secrets["gsheets"],
            scopes=SCOPES
        )
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key("1i-RoIG-BjnVneZ9UM2Lv-cy8e97jTdJdSeNYYADT3wM")
        worksheet = spreadsheet.sheet1
        
        # Check headers inside the thread as well
        if not worksheet.row_values(1):
             worksheet.insert_row(['Session ID', 'Question Number', 'User Vote', 'Correct Answer', 'Timestamp'], 1)

        new_data = [
            session_id,
            question_num,
            user_vote,
            correct_answer,
            datetime.now().isoformat()
        ]
        worksheet.append_row(new_data)
    except Exception as e:
        # In a thread, we can't update the UI. Print to console for debugging.
        print(f"Error saving vote in background thread: {repr(e)}")

def get_stats():
    """Get all votes from Google Sheets using Streamlit's connection."""
    try:
        # Get credentials from secrets
        credentials_dict = st.secrets["gsheets"]
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        gc = gspread.authorize(credentials)
        
        # Open the spreadsheet and get data
        spreadsheet = gc.open_by_key("1i-RoIG-BjnVneZ9UM2Lv-cy8e97jTdJdSeNYYADT3wM")
        worksheet = spreadsheet.sheet1
        ensure_headers(worksheet)
        data = worksheet.get_all_records()
        
        # Convert to the same format as before
        return [{
            'session_id': record['Session ID'],
            'question_num': int(record['Question Number']),
            'user_vote': record['User Vote'],
            'correct_answer': record['Correct Answer'],
            'timestamp': record['Timestamp']
        } for record in data]
    except Exception as e:
        st.error(f"Failed to get stats: {repr(e)}")
        return []

# Main app
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Agent or Workflow?</h1>
        <h3>Mapping the Community's Understanding</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.quiz_started:
        # Landing page
        st.markdown("""
        ### Everyone wants to build "AI agents" but nobody really knows what they are.
        
        **Why does this matter?** The agent vs workflow distinction is crucial for:
        - **Architecture decisions**: Should you build a fixed pipeline or dynamic system?
        - **Reliability expectations**: Workflows are predictable, agents are autonomous but unpredictable
        - **Cost implications**: Agents can make more LLM calls than anticipated
        - **Debugging complexity**: Workflows follow known paths, agents create emergent behaviors
        
        This quiz collects the public's intuition about this fundamental distinction. The boundary is often blurry, and there's no universal agreement on definitions.
        
        **Working definitions:**
        - **Workflow**: LLMs and tools orchestrated through predefined code paths
        - **Agent**: LLM dynamically directs its own processes and tool usage
        
        📖 **Deep dive:** [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) by Anthropic
        
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
        
        # Disable the button if an answer has already been submitted for this question.
        already_answered = len(st.session_state.user_answers) > current_q
        
        def handle_vote(vote):
            # This check is crucial to prevent multiple rapid submissions.
            if not already_answered:
                st.session_state.user_answers.append(vote)
                # Run the save operation in a background thread to keep UI responsive.
                threading.Thread(
                    target=save_vote_threaded,
                    args=(
                        current_q,
                        vote,
                        question_data['correct'],
                        st.session_state.session_id,
                        st.secrets
                    ),
                    daemon=True
                ).start()
                # Advance the quiz immediately. The user doesn't wait for the save to complete.
                advance_question()

        with col1:
            st.button(
                "🤖 AGENT",
                use_container_width=True,
                on_click=handle_vote,
                args=("Agent",),
                disabled=already_answered,
            )
        
        with col2:
            st.button(
                "⚙️ WORKFLOW",
                use_container_width=True,
                on_click=handle_vote,
                args=("Workflow",),
                disabled=already_answered,
            )
    
    else:
        # Quiz completed - show results
        show_final_results()

def advance_question():
    if st.session_state.current_question < len(QUIZ_DATA) - 1:
        st.session_state.current_question += 1
    else:
        st.session_state.quiz_completed = True
    st.rerun()

def show_final_results():
    st.markdown("## 🎉 Quiz Complete!")
    
    st.markdown("""
    **Remember:** The agent/workflow boundary is blurry and there's no universal agreement. 
    These explanations represent my perspective, but your intuitions matter too!
    """)
    
    # Calculate score
    correct_count = 0
    min_len = min(len(st.session_state.user_answers), len(QUIZ_DATA))
    for i in range(min_len):
        user_answer = st.session_state.user_answers[i]
        if user_answer == QUIZ_DATA[i]['correct']:
            correct_count += 1
    
    score_pct = (correct_count / len(QUIZ_DATA)) * 100
    
    st.markdown(f"### Your Answers vs. My Perspective: {correct_count}/{len(QUIZ_DATA)} matches ({score_pct:.0f}%)")
    
    # Get stats for charts
    stats = get_stats()
    
    # Show detailed explanations with integrated charts
    st.markdown("### 📝 My Reasoning + Community Votes")
    
    for i in range(min_len):
        question_data = QUIZ_DATA[i]
        user_answer = st.session_state.user_answers[i]
        my_answer = question_data['correct']
        is_match = user_answer == my_answer
        
        # Calculate community stats for this question
        question_votes = [v for v in stats if v['question_num'] == i] if stats else []
        total_votes = len(question_votes)
        
        if total_votes > 0:
            agent_votes = len([v for v in question_votes if v['user_vote'] == 'Agent'])
            agent_pct = (agent_votes / total_votes) * 100
            workflow_pct = 100 - agent_pct
        else:
            agent_pct = workflow_pct = 0
        
        with st.expander(f"{question_data['title']} - You: {user_answer}, Me: {my_answer} {'✅' if is_match else '🤔'} | 📊 {total_votes} community votes"):
            
            # Show community voting chart if we have data
            if total_votes > 0:
                st.markdown("**Community Voting:**")
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style=\"background: linear-gradient(to right, #ef4444 0%, #ef4444 {agent_pct}%, #64748b {agent_pct}%, #64748b 100%); height: 30px; border-radius: 15px; display: flex; align-items: center; color: white; font-weight: bold; padding: 0 10px;\">
                        🤖 {agent_pct:.0f}% Agent | ⚙️ {workflow_pct:.0f}% Workflow
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    your_vote_emoji = "🤖" if user_answer == 'Agent' else "⚙️"
                    st.markdown(f"**You:** {your_vote_emoji} {user_answer}")
                
                with col3:
                    my_opinion_emoji = "🤖" if my_answer == 'Agent' else "⚙️"
                    st.markdown(f"**Me:** {my_opinion_emoji} {my_answer}")
                
                st.markdown("---")
            
            # Show reasoning
            st.markdown(f"**My reasoning:** {question_data['explanation']}")
            st.markdown("*Remember - smart people disagree on these classifications!*")
    
    # ZenML CTA
    st.markdown("---")
    st.markdown("### 🚀 Ready to Build Agentic Workflows?")
    st.markdown("""
    See how these concepts work in practice! Check out an implementation of a **Deep Research Agent** - 
    a workflow with sub-agents that conducts comprehensive research on any topic using dynamic tool selection and iterative refinement.
    
    🔍 **[Explore the Deep Research Agent →](https://github.com/zenml-io/zenml-projects/tree/main/deep_research)**
    
    *Built with ZenML - the framework for production ML pipelines and agentic workflows*
    """)
    
    # Demo CTA
    st.markdown("""
    ### 💬 Want to Discuss Agentic Workflows?
    
    Book a personalized demo with our team to explore how ZenML can help you build and deploy your own agentic workflows.
    
    🎯 **[Book Your Demo →](https://zenml.io/book-your-demo)**
    """)
    
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
