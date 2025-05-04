import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

# Configure Gemini - using the latest Flash model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Page configuration
st.set_page_config(
    page_title="Campus Recruitment Test Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff;
        border-radius: 10px;
    }
    .stSelectbox>div>div>select {
        background-color: #ffffff;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .section-box {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .header { color: #2c3e50; }
    .question-card {
        background-color: #f9f9f9;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 5px;
    }
    .progress-bar {
        height: 10px;
        background-color: #e0e0e0;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .progress {
        height: 100%;
        background-color: #4CAF50;
        border-radius: 5px;
        transition: width 0.5s;
    }
    </style>
""", unsafe_allow_html=True)

# Session state
if 'test_data' not in st.session_state:
    st.session_state.test_data = {
        'job_description': '',
        'role': '',
        'skills_required': '',
        'sections': [],
        'generated_test': None,
        'generation_progress': 0
    }

st.title("\U0001f3db️ Campus Recruitment Test Generator")
st.markdown("---")

page = st.sidebar.radio("Navigation", ["Input Details", "Generate Test", "View Test"])

def simulate_progress():
    progress_bar = st.empty()
    for percent_complete in range(0, 101, 5):
        st.session_state.test_data['generation_progress'] = percent_complete
        progress_bar.markdown(f"""
        <div class="progress-bar">
            <div class="progress" style="width:{percent_complete}%"></div>
        </div>
        <p>Generating test... {percent_complete}%</p>
        """, unsafe_allow_html=True)
        time.sleep(0.1)

if page == "Input Details":
    st.header("\U0001f4cb Enter Company Recruitment Details")
    with st.form("job_details_form"):
        st.session_state.test_data['role'] = st.text_input("Job Role")
        st.session_state.test_data['skills_required'] = st.text_area("Skills Required")
        st.session_state.test_data['job_description'] = st.text_area("Job Description", height=200)

        default_sections = ["MCQ", "Coding", "DBMS", "Programming Language", "Aptitude"]
        selected_sections = st.multiselect("Select sections", default_sections, default=default_sections)
        custom_section = st.text_input("Add custom section")
        if custom_section:
            selected_sections.append(custom_section)

        st.session_state.test_data['sections'] = selected_sections

        if st.form_submit_button("Save Details"):
            st.success("Details saved successfully! Proceed to 'Generate Test' page.")

elif page == "Generate Test":
    st.header("⚙️ Generate Recruitment Test")

    if not st.session_state.test_data['job_description']:
        st.warning("Please enter job details on the 'Input Details' page first.")
    else:
        st.subheader("Review Details")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Role:** {st.session_state.test_data['role']}")
            st.markdown(f"**Skills:** {st.session_state.test_data['skills_required']}")
        with col2:
            st.markdown(f"**Sections:** {', '.join(st.session_state.test_data['sections'])}")

        st.subheader("Test Parameters")
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            mcq_count = st.slider("MCQs per section", 5, 20, 10) if "MCQ" in st.session_state.test_data['sections'] else 0
        with col2:
            coding_questions = st.slider("Coding questions", 1, 5, 2) if "Coding" in st.session_state.test_data['sections'] else 0
            time_limit = st.slider("Test duration (minutes)", 30, 180, 60)

        if st.button("Generate Test"):
            with st.spinner("Generating test questions..."):
                simulate_progress()
                prompt = f"""
                Generate a campus recruitment test in JSON for the role: {st.session_state.test_data['role']}
                Job Description: {st.session_state.test_data['job_description']}
                Skills: {st.session_state.test_data['skills_required']}
                Difficulty: {difficulty}, Duration: {time_limit} mins
                Sections: {', '.join(st.session_state.test_data['sections'])}
                MCQs per section: {mcq_count}, Coding Questions: {coding_questions}
                Ensure output is valid JSON only.
                """
                try:
                    response = model.generate_content(prompt)
                    raw = response.text
                    if '```json' in raw:
                        raw = raw.split('```json')[1].split('```')[0].strip()
                    elif '```' in raw:
                        raw = raw.split('```')[1].strip()

                    test_data = json.loads(raw)
                    st.session_state.test_data['generated_test'] = test_data
                    st.success("Test generated successfully! Proceed to 'View Test' page.")
                except json.JSONDecodeError as e:
                    st.error("Failed to parse JSON: " + str(e))
                    st.text_area("Raw Output", raw, height=300)
                except Exception as e:
                    st.error("Error: " + str(e))

elif page == "View Test":
    st.header("\U0001f4c4 Generated Recruitment Test")
    if not st.session_state.test_data['generated_test']:
        st.warning("Please generate a test first.")
    else:
        data = st.session_state.test_data['generated_test']
        st.markdown(f"## {data['test_title']}")
        st.markdown(f"**Duration:** {data['total_duration']} mins | **Marks:** {data['total_marks']}")

        with st.expander("\U0001f4ca Grading Rubric"):
            for level, rule in data['grading_rubric'].items():
                st.markdown(f"**{level.capitalize()}** ({rule['score_range']}): {rule['description']}")

        for section in data['sections']:
            with st.expander(f"{section['section_name']} (Marks: {section['total_marks']})"):
                st.markdown(f"*{section['section_instructions']}*")
                for i, q in enumerate(section['questions'], 1):
                    st.markdown(f"**Q{i}: {q['question_text']}** [{q['marks']} mark(s)]")
                    if q['question_type'].lower() == 'mcq':
                        for idx, opt in enumerate(q['options'], 1):
                            st.markdown(f"{idx}. {opt}")
                        st.markdown(f"**Answer:** {q['correct_answer']}")
                    elif q['question_type'].lower() == 'coding':
                        st.markdown("**Sample Input:**")
                        st.code(q.get('sample_input', ''), language="python")
                        st.markdown("**Sample Output:**")
                        st.code(q.get('sample_output', ''), language="python")
                        if q.get('explanation'):
                            st.markdown(f"_Explanation_: {q['explanation']}")

        # Download Button
        st.download_button(
            label="📥 Download Test JSON",
            data=json.dumps(data, indent=4),
            file_name="campus_recruitment_test.json",
            mime="application/json"
        )
