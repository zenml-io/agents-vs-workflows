import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Quiz Results Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Data from the main app (for context) ---
QUIZ_DATA = [
    {"title": "Prompt Chaining", "correct": "Workflow"},
    {"title": "Tool-Calling Agent", "correct": "Agent"},
    {"title": "Routing", "correct": "Workflow"},
    {"title": "Parallelization", "correct": "Workflow"},
    {"title": "Orchestrator-Worker", "correct": "Workflow"},
    {"title": "Research Agent", "correct": "Agent"},
    {"title": "Evaluator-Optimizer", "correct": "Workflow"}
]
QUESTION_TITLES = {i: d['title'] for i, d in enumerate(QUIZ_DATA)}

# --- Google Sheets Connection ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_data(ttl=60) # Cache data for 60 seconds
def get_data_from_gsheet():
    """Fetches and returns the quiz data from the Google Sheet."""
    try:
        creds_json = st.secrets["gsheets"]
        creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key("1i-RoIG-BjnVneZ9UM2Lv-cy8e97jTdJdSeNYYADT3wM")
        worksheet = spreadsheet.sheet1
        rows = worksheet.get_all_records()
        df = pd.DataFrame(rows)
        # Basic data cleaning
        df['Question Number'] = pd.to_numeric(df['Question Number'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {repr(e)}")
        return pd.DataFrame()

# --- Main Dashboard ---
st.title("📊 Agents vs. Workflows Quiz Results")
st.markdown("This dashboard visualizes the community's votes and understanding.")

df = get_data_from_gsheet()

if df.empty:
    st.warning("No data loaded. Please check the connection or sheet contents.")
    st.stop()

# --- Key Metrics ---
st.header("Key Metrics")
total_sessions = df['Session ID'].nunique()
total_votes = len(df)
latest_vote_time = df['Timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')

col1, col2, col3 = st.columns(3)
col1.metric("Total Unique Participants", f"{total_sessions}")
col2.metric("Total Votes Cast", f"{total_votes}")
col3.metric("Last Vote Received", f"{latest_vote_time}")

st.markdown("---")

# --- Visualizations ---
st.header("Visual Analysis")

# 1. Overall Vote Distribution
st.subheader("Overall: Agent vs. Workflow")
vote_counts = df['User Vote'].value_counts()
fig_pie = px.pie(
    values=vote_counts.values, 
    names=vote_counts.index, 
    title="Total Votes: Agent vs. Workflow",
    color=vote_counts.index,
    color_discrete_map={'Agent': '#ef4444', 'Workflow': '#64748b'}
)
st.plotly_chart(fig_pie, use_container_width=True)


# 2. Per-Question Breakdown
st.subheader("How did the community vote on each question?")
df['Question Title'] = df['Question Number'].map(QUESTION_TITLES)
votes_by_question = df.groupby(['Question Title', 'User Vote']).size().reset_index(name='count')

fig_bar = px.bar(
    votes_by_question, 
    x='Question Title', 
    y='count', 
    color='User Vote',
    barmode='group',
    title="Votes per Question",
    labels={'count': 'Number of Votes', 'Question Title': 'Question'},
    color_discrete_map={'Agent': '#ef4444', 'Workflow': '#64748b'}
)
fig_bar.update_xaxes(categoryorder='array', categoryarray=[q['title'] for q in QUIZ_DATA])
st.plotly_chart(fig_bar, use_container_width=True)


# 3. Community vs. "Correct" Answer
st.subheader("How often did the community agree with the 'correct' answer?")
df['Is Correct'] = df.apply(lambda row: row['User Vote'] == QUIZ_DATA[row['Question Number']]['correct'], axis=1)
agreement_rate = df.groupby('Question Title')['Is Correct'].mean().reset_index()
agreement_rate['Is Correct'] *= 100 # Convert to percentage

fig_agreement = px.bar(
    agreement_rate,
    x='Question Title',
    y='Is Correct',
    title='Community Agreement Rate with "Correct" Answer',
    labels={'Is Correct': 'Agreement Rate (%)', 'Question Title': 'Question'},
    color_discrete_sequence=['#7C3AED']
)
fig_agreement.update_yaxes(range=[0, 100])
fig_agreement.update_xaxes(categoryorder='array', categoryarray=[q['title'] for q in QUIZ_DATA])
st.plotly_chart(fig_agreement, use_container_width=True)


# --- Raw Data ---
with st.expander("View Raw Data"):
    st.dataframe(df) 