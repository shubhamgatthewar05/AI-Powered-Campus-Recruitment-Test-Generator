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
model = genai.GenerativeModel('gemini-1.5-flash')  # Using the Flash model

# Page configuration
st.set_page_config(
    page_title="Campus Recruitment Test Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
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
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
    }
    .header {
        color: #2c3e50;
    }
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

# Session state initialization
if 'test_data' not in st.session_state:
    st.session_state.test_data = {
        'job_description': '',
        'role': '',
        'skills_required': '',
        'sections': [],
        'generated_test': None,
        'generation_progress': 0
    }

# App header
st.title("🏛️ Campus Recruitment Test Generator")
st.markdown("---")

# Page navigation
page = st.sidebar.radio("Navigation", ["Input Details", "Generate Test", "View Test"])

def simulate_progress():
    """Simulate progress bar for test generation"""
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
    st.session_state.test_data['generation_progress'] = 100

# Input Details Page
if page == "Input Details":
    st.header("📋 Enter Company Recruitment Details")
    
    with st.form("job_details_form"):
        st.session_state.test_data['role'] = st.text_input("Job Role", placeholder="e.g., Software Engineer, Data Analyst")
        st.session_state.test_data['skills_required'] = st.text_area("Skills Required (comma separated)", 
                                                                    placeholder="e.g., Python, SQL, Data Structures, Algorithms")
        st.session_state.test_data['job_description'] = st.text_area("Job Description", 
                                                                   placeholder="Paste the full job description here",
                                                                   height=200)
        
        # Section selection
        st.subheader("Test Sections")
        default_sections = ["MCQ", "Coding", "DBMS", "Programming Language", "Aptitude"]
        selected_sections = st.multiselect("Select sections for the test", 
                                          default_sections, 
                                          default=default_sections)
        
        # Custom section addition
        custom_section = st.text_input("Add custom section (optional)", placeholder="e.g., System Design")
        if custom_section:
            selected_sections.append(custom_section)
        
        st.session_state.test_data['sections'] = selected_sections
        
        submitted = st.form_submit_button("Save Details")
        if submitted:
            st.success("Details saved successfully! Proceed to 'Generate Test' page.")

# Generate Test Page
elif page == "Generate Test":
    st.header("⚙️ Generate Recruitment Test")
    
    if not st.session_state.test_data['job_description']:
        st.warning("Please enter job details on the 'Input Details' page first.")
    else:
        st.subheader("Review Details")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Role:** {st.session_state.test_data['role']}")
            st.markdown(f"**Skills Required:** {st.session_state.test_data['skills_required']}")
        with col2:
            st.markdown(f"**Sections:** {', '.join(st.session_state.test_data['sections'])}")
        
        st.subheader("Test Parameters")
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Test Difficulty", ["Easy", "Medium", "Hard"])
            mcq_count = st.slider("MCQs per section", 5, 20, 10) if "MCQ" in st.session_state.test_data['sections'] else 0
        with col2:
            coding_questions = st.slider("Coding questions", 1, 5, 2) if "Coding" in st.session_state.test_data['sections'] else 0
            time_limit = st.slider("Test duration (minutes)", 30, 180, 60)
        
        if st.button("Generate Test"):
            with st.spinner("Generating test questions..."):
                # Show progress bar
                simulate_progress()
                
                # Prepare prompt for Gemini
                prompt = f"""
                Generate a comprehensive campus recruitment test in valid JSON format for the role of {st.session_state.test_data['role']}.
                The test should be tailored to the specific job requirements and include various question types.
                
                ### Requirements:
                - Job Description: {st.session_state.test_data['job_description']}
                - Required Skills: {st.session_state.test_data['skills_required']}
                - Test Difficulty: {difficulty}
                - Test Duration: {time_limit} minutes
                - Sections: {', '.join(st.session_state.test_data['sections'])}
                - MCQ Count per section: {mcq_count if mcq_count else 'N/A'}
                - Coding Questions: {coding_questions if coding_questions else 'N/A'}
                
                ### Output Format:
                {{
                    "test_title": "string",
                    "total_duration": number,
                    "total_marks": number,
                    "sections": [
                        {{
                            "section_name": "string",
                            "section_instructions": "string",
                            "questions": [
                                {{
                                    "question_text": "string",
                                    "question_type": "string (MCQ/CODING/ESSAY/etc.)",
                                    "options": ["string"] (only for MCQ),
                                    "correct_answer": "string",
                                    "marks": number,
                                    "sample_input": "string" (for coding),
                                    "sample_output": "string" (for coding),
                                    "explanation": "string" (optional)
                                }}
                            ],
                            "total_marks": number
                        }}
                    ],
                    "grading_rubric": {{
                        "excellent": {{
                            "score_range": "string",
                            "description": "string"
                        }},
                        "good": {{
                            "score_range": "string",
                            "description": "string"
                        }},
                        "average": {{
                            "score_range": "string",
                            "description": "string"
                        }},
                        "poor": {{
                            "score_range": "string",
                            "description": "string"
                        }}
                    }}
                }}
                
                ### Important Notes:
                1. Generate valid JSON ONLY - no additional text or markdown
                2. Ensure all special characters are properly escaped
                3. Questions should be relevant to the specified role and skills
                4. Include a comprehensive grading rubric
                5. For coding questions, provide clear sample inputs/outputs
                6. For MCQ questions, provide 4 options and mark the correct one
                """
                
                try:
                    response = model.generate_content(prompt)
                    generated_content = response.text
                    
                    # Clean the response
                    if '```json' in generated_content:
                        generated_content = generated_content.split('```json')[1].split('```')[0].strip()
                    elif '```' in generated_content:
                        generated_content = generated_content.split('```')[1].strip()
                    
                    # Parse the JSON
                    test_data = json.loads(generated_content)
                    st.session_state.test_data['generated_test'] = test_data
                    st.success("Test generated successfully! Proceed to 'View Test' page.")
                except json.JSONDecodeError as e:
                    st.error(f"Failed to parse JSON response: {str(e)}")
                    st.text_area("Raw Response", generated_content, height=200)
                except Exception as e:
                    st.error(f"Error generating test: {str(e)}")
                    st.write("Please try again or adjust your input parameters.")

# View Test Page
elif page == "View Test":
    st.header("📄 Generated Recruitment Test")
    
    if not st.session_state.test_data.get('generated_test'):
        st.warning("Please generate a test first on the 'Generate Test' page.")
    else:
        test_data = st.session_state.test_data['generated_test']
        
        st.markdown(f"## {test_data['test_title']}")
        st.markdown(f"**Total Duration:** {test_data['total_duration']} minutes | **Total Marks:** {test_data['total_marks']}")
        
        # Display grading rubric
        with st.expander("📊 Grading Rubric"):
            for level, criteria in test_data.get('grading_rubric', {}).items():
                st.markdown(f"**{level.capitalize()} ({criteria['score_range']})**: {criteria['description']}")
        
        st.markdown("---")
        
        for section in test_data['sections']:
            with st.expander(f"### {section['section_name']} (Total Marks: {section['total_marks']})"):
                st.markdown(f"*{section['section_instructions']}*")
                st.markdown("---")
                
                for i, question in enumerate(section['questions'], 1):
                    with st.container():
                        st.markdown(f"**Q{i}. {question['question_text']}** [{question['marks']} mark(s)]")
                        
                        if question['question_type'].lower() == 'mcq':
                            for j, option in enumerate(question.get('options', []), 1):
                                st.markdown(f"{j}. {option}")
                            with st.expander("View Answer"):
                                st.markdown(f"**Correct Answer:** {question.get('correct_answer', 'Not provided')}")
                                if 'explanation' in question:
                                    st.markdown(f"**Explanation:** {question['explanation']}")
                        
                        elif question['question_type'].lower() == 'coding':
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Sample Input:**")
                                st.code(question.get('sample_input', 'Not provided'))
                            with col2:
                                st.markdown("**Sample Output:**")
                                st.code(question.get('sample_output', 'Not provided'))
                            with st.expander("View Expected Solution"):
                                st.markdown(f"**Approach:** {question.get('explanation', 'Not provided')}")
                        
                        st.markdown("")
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download Test as JSON",
                data=json.dumps(test_data, indent=2),
                file_name=f"{st.session_state.test_data['role'].replace(' ', '_')}_recruitment_test.json",
                mime="application/json"
            )
        with col2:
            # Generate a printable version
            printable_content = f"""
            <html>
            <head>
                <title>{test_data['test_title']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    h1 {{ color: #2c3e50; }}
                    .section {{ margin-bottom: 30px; }}
                    .question {{ margin-bottom: 20px; }}
                    .options {{ margin-left: 20px; }}
                    .code {{ background: #f5f5f5; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>{test_data['test_title']}</h1>
                <p><strong>Total Duration:</strong> {test_data['total_duration']} minutes</p>
                <p><strong>Total Marks:</strong> {test_data['total_marks']}</p>
                <hr>
            """
            
            for section in test_data['sections']:
                printable_content += f"""
                <div class="section">
                    <h2>{section['section_name']} (Total Marks: {section['total_marks']})</h2>
                    <p><em>{section['section_instructions']}</em></p>
                    <hr>
                """
                
                for i, question in enumerate(section['questions'], 1):
                    printable_content += f"""
                    <div class="question">
                        <p><strong>Q{i}. {question['question_text']}</strong> [{question['marks']} mark(s)]</p>
                    """
                    
                    if question['question_type'].lower() == 'mcq':
                        printable_content += "<div class='options'>"
                        for j, option in enumerate(question.get('options', []), 1):
                            printable_content += f"<p>{j}. {option}</p>"
                        printable_content += "</div>"
                    
                    elif question['question_type'].lower() == 'coding':
                        printable_content += """
                        <div style="display: flex;">
                            <div style="flex: 1;">
                                <p><strong>Sample Input:</strong></p>
                                <pre class="code">""" + question.get('sample_input', 'Not provided') + """</pre>
                            </div>
                            <div style="flex: 1;">
                                <p><strong>Sample Output:</strong></p>
                                <pre class="code">""" + question.get('sample_output', 'Not provided') + """</pre>
                            </div>
                        </div>
                        """
                    
                    printable_content += "</div>"
                
                printable_content += "</div>"
            
            printable_content += "</body></html>"
            
            st.download_button(
                label="Download Printable Test (HTML)",
                data=printable_content,
                file_name=f"{st.session_state.test_data['role'].replace(' ', '_')}_recruitment_test.html",
                mime="text/html"
            )
            st.markdown(f"{j}. {option}")
            st.markdown(f"**Correct Answer:** {question['correct_answer']}")
            if 'explanation' in question and question['explanation']:
                st.markdown(f"**Explanation:** {question['explanation']}")

            elif question['question_type'].lower() == 'coding':
                st.markdown("```python")
                st.markdown(f"# Sample Input:\n{question.get('sample_input', 'N/A')}")
                st.markdown(f"# Sample Output:\n{question.get('sample_output', 'N/A')}")
                st.markdown("```")
                if 'explanation' in question and question['explanation']:
                    st.markdown(f"**Explanation:** {question['explanation']}")
                        
            else:
                st.markdown("_Question type not recognized or not supported yet._")
