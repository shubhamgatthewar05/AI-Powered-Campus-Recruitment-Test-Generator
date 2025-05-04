import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

# Load environment variables
load_dotenv()

# Configure Gemini - using the latest Flash model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# MongoDB configuration
mongo_uri = os.getenv("mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client.campus_recruitment
tests_collection = db.tests
responses_collection = db.responses
users_collection = db.users

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
    .code-editor {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
        min-height: 200px;
    }
    .test-response-form {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .student-view {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .teacher-view {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .dashboard-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .card-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .card-title {
        color: #666;
        font-size: 16px;
    }
    .floating-timer {
        position: fixed;
        top: 70px;
        right: 20px;
        background-color: #4CAF50;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        z-index: 1000;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        text-align: center;
    }
    .timer-warning {
        background-color: #FF5722 !important;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .tab-content {
        padding: 20px;
        background-color: white;
        border-radius: 0 0 10px 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
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
        'generation_progress': 0,
        'student_responses': {},
        'current_test_id': None,
        'test_submitted': False,
        'user_type': None,
        'student_name': '',
        'student_email': '',
        'logged_in': False,
        'username': '',
        'user_id': None
    }

# Helper functions
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

def evaluate_with_llm(student_responses, test_data):
    """Evaluate student responses using Gemini LLM"""
    all_evaluations = {}
    
    for section in test_data['sections']:
        for question in section['questions']:
            question_id = question['question_id']
            if question_id in student_responses['responses']:
                response = student_responses['responses'][question_id]
                
                # Prepare prompt for evaluation
                prompt = f"""
                Evaluate the following student response as a highly experienced software engineering interviewer.
                
                Question: {question['question_text']}
                Question Type: {question['question_type']}
                Maximum Marks: {question['marks']}
                
                """
                
                if question['question_type'].lower() == 'mcq':
                    prompt += f"""
                    Correct Answer: {question.get('correct_answer', 'N/A')}
                    Student Answer: {response.get('response', 'No answer')}
                    
                    Award {question['marks']} marks if the answer is exactly correct.
                    Award 0 marks if the answer is incorrect.
                    """
                elif question['question_type'].lower() == 'coding':
                    prompt += f"""
                    Student Code:
                    ```
                    {response.get('response', '# No code submitted')}
                    ```
                    
                    Test Cases:
                    """
                    for test_case in question.get('test_cases', []):
                        prompt += f"Input: {test_case.get('input', '')}, Expected Output: {test_case.get('output', '')}\n"
                    
                    prompt += f"""
                    Evaluate the code for:
                    1. Correctness - Does it provide the expected output for all test cases?
                    2. Efficiency - Is the algorithm efficient?
                    3. Code quality - Is the code well-structured and readable?
                    
                    Award marks out of {question['marks']} based on these criteria.
                    """
                else:
                    prompt += f"""
                    Expected Answer Key Points: {question.get('correct_answer', 'Not provided')}
                    Student Answer: {response.get('response', 'No answer')}
                    
                    Award marks out of {question['marks']} based on accuracy and completeness.
                    """
                
                prompt += """
                Provide your evaluation in the following JSON format only:
                {
                    "marks": [number between 0 and max marks],
                    "feedback": "Detailed explanation for the marks awarded"
                }
                """
                
                try:
                    evaluation_response = model.generate_content(prompt)
                    evaluation_text = evaluation_response.text
                    
                    # Extract JSON from response
                    if '```json' in evaluation_text:
                        evaluation_text = evaluation_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in evaluation_text:
                        evaluation_text = evaluation_text.split('```')[1].strip()
                    
                    evaluation = json.loads(evaluation_text)
                    
                    # Update the response object
                    all_evaluations[question_id] = {
                        "score": evaluation["marks"],
                        "feedback": evaluation["feedback"],
                        "evaluated": True
                    }
                except Exception as e:
                    all_evaluations[question_id] = {
                        "score": 0,
                        "feedback": f"Automatic evaluation failed: {str(e)}",
                        "evaluated": False
                    }
    
    return all_evaluations

def get_download_link(df, filename, text):
    """Generate a download link for a dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def create_pdf_report(test_data, responses):
    """Create a PDF report for test results"""
    # In a real app, you would generate a PDF here
    # For now, we'll just create a downloadable CSV
    data = []
    for response in responses:
        data.append({
            "Student Name": response["student_name"],
            "Email": response["student_email"],
            "Score": response.get("score", 0),
            "Time Taken (min)": round((response["end_time"] - response["start_time"]).total_seconds() / 60, 2)
        })
    
    return pd.DataFrame(data)

# Login/Registration System
def login_page():
    st.header("🔐 Login")
    
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            user_type = st.selectbox("Login As", ["Teacher", "Student"])
            
            submitted = st.form_submit_button("Login")
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    # Check credentials
                    user = users_collection.find_one({
                        "username": username,
                        "user_type": user_type.lower()
                    })
                    
                    if user and user["password"] == password:  # In production, use proper password hashing
                        st.session_state.test_data['logged_in'] = True
                        st.session_state.test_data['user_type'] = user_type.lower()
                        st.session_state.test_data['username'] = username
                        st.session_state.test_data['user_id'] = str(user["_id"])
                        if user_type.lower() == "student":
                            st.session_state.test_data['student_name'] = user.get("full_name", username)
                            st.session_state.test_data['student_email'] = user.get("email", "")
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
    
    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            new_user_type = st.selectbox("Register As", ["Teacher", "Student"])
            
            submitted = st.form_submit_button("Register")
            if submitted:
                if not new_username or not new_password or not confirm_password or not full_name or not email:
                    st.error("Please fill all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Check if username already exists
                    existing_user = users_collection.find_one({"username": new_username})
                    if existing_user:
                        st.error("Username already exists")
                    else:
                        # Register user
                        user_record = {
                            "username": new_username,
                            "password": new_password,  # In production, hash the password
                            "full_name": full_name,
                            "email": email,
                            "user_type": new_user_type.lower(),
                            "created_at": datetime.now()
                        }
                        users_collection.insert_one(user_record)
                        st.success("Registration successful! Please login.")

# App header
st.title("🏛️ Campus Recruitment Test Generator")
st.markdown("---")

# Check if user is logged in
if not st.session_state.test_data.get('logged_in', False):
    login_page()
else:
    # Logout button in the sidebar
    if st.sidebar.button("Logout"):
        st.session_state.test_data = {
            'job_description': '',
            'role': '',
            'skills_required': '',
            'sections': [],
            'generated_test': None,
            'generation_progress': 0,
            'student_responses': {},
            'current_test_id': None,
            'test_submitted': False,
            'user_type': None,
            'student_name': '',
            'student_email': '',
            'logged_in': False,
            'username': '',
            'user_id': None
        }
        st.rerun()
    
    # Show user info
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.test_data['username']} ({st.session_state.test_data['user_type'].capitalize()})")
    st.sidebar.markdown("---")
    
    # Page navigation based on user type
    if st.session_state.test_data['user_type'] == 'teacher':
        pages = ["Dashboard", "Input Details", "Generate Test", "View Tests", "Evaluate Responses", "Analytics"]
        page = st.sidebar.radio("Navigation", pages)
    elif st.session_state.test_data['user_type'] == 'student':
        pages = ["Dashboard", "Take Test", "View Results"]
        page = st.sidebar.radio("Navigation", pages)
    else:
        st.stop()
    
    # Dashboard Page (Both)
    if page == "Dashboard":
        if st.session_state.test_data['user_type'] == 'teacher':
            st.header("📊 Teacher Dashboard")
            
            # Get statistics
            test_count = tests_collection.count_documents({})
            response_count = responses_collection.count_documents({})
            evaluated_count = responses_collection.count_documents({"evaluated": True})
            
            # Display stats in cards
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                <div class="dashboard-card">
                    <p class="card-title">Tests Created</p>
                    <p class="card-value" style="color: #4CAF50;">{}</p>
                </div>
                """.format(test_count), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="dashboard-card">
                    <p class="card-title">Total Responses</p>
                    <p class="card-value" style="color: #2196F3;">{}</p>
                </div>
                """.format(response_count), unsafe_allow_html=True)
            
            with col3:
                evaluation_rate = (evaluated_count / response_count * 100) if response_count > 0 else 0
                st.markdown("""
                <div class="dashboard-card">
                    <p class="card-title">Evaluation Rate</p>
                    <p class="card-value" style="color: #FF9800;">{:.1f}%</p>
                </div>
                """.format(evaluation_rate), unsafe_allow_html=True)
            
            # Recent tests
            st.subheader("Recent Tests")
            recent_tests = list(tests_collection.find().sort("created_at", -1).limit(5))
            
            if not recent_tests:
                st.info("No tests created yet. Go to 'Input Details' to create your first test.")
            else:
                for test in recent_tests:
                    response_count = responses_collection.count_documents({"test_id": str(test['_id'])})
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{test['test_data']['test_title']}**")
                        st.markdown(f"Role: {test['role']} | Created: {test['created_at'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.markdown(f"**{response_count}** responses")
                    with col3:
                        if st.button("View", key=f"view_dash_{test['_id']}"):
                            st.session_state['view_test_id'] = str(test['_id'])
                            st.session_state['current_page'] = "View Tests"
                            st.rerun()
                    st.markdown("---")
            
            # Quick links
            st.subheader("Quick Actions")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Create New Test"):
                    st.session_state['current_page'] = "Input Details"
                    st.rerun()
            with col2:
                if st.button("Evaluate Responses"):
                    st.session_state['current_page'] = "Evaluate Responses"
                    st.rerun()
        
        else:  # Student Dashboard
            st.header("📚 Student Dashboard")
            
            # Student stats
            tests_taken = responses_collection.count_documents({"student_email": st.session_state.test_data['student_email']})
            evaluated_tests = responses_collection.count_documents({"student_email": st.session_state.test_data['student_email'], "evaluated": True})
            
            # Display stats
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                <div class="dashboard-card">
                    <p class="card-title">Tests Taken</p>
                    <p class="card-value" style="color: #4CAF50;">{}</p>
                </div>
                """.format(tests_taken), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="dashboard-card">
                    <p class="card-title">Evaluated Tests</p>
                    <p class="card-value" style="color: #2196F3;">{}</p>
                </div>
                """.format(evaluated_tests), unsafe_allow_html=True)
            
            # Available tests
            st.subheader("Available Tests")
            available_tests = list(tests_collection.find({}, {"test_data.test_title": 1, "role": 1, "_id": 1}))
            
            if not available_tests:
                st.info("No tests available. Please check back later.")
            else:
                for test in available_tests:
                    # Check if student has already taken this test
                    already_taken = responses_collection.count_documents({
                        "test_id": str(test['_id']),
                        "student_email": st.session_state.test_data['student_email']
                    }) > 0
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{test['test_data']['test_title']}**")
                        st.markdown(f"Role: {test['role']}")
                    with col2:
                        if already_taken:
                            st.success("Completed")
                        else:
                            if st.button("Take Test", key=f"take_{test['_id']}"):
                                st.session_state.test_data['current_test_id'] = str(test['_id'])
                                st.session_state['current_page'] = "Take Test"
                                st.rerun()
                    st.markdown("---")
    
    # Input Details Page (Teacher only)
    elif page == "Input Details" and st.session_state.test_data['user_type'] == 'teacher':
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
    
    # Generate Test Page (Teacher only)
    elif page == "Generate Test" and st.session_state.test_data['user_type'] == 'teacher':
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
                                        "question_id": "string (unique identifier)",
                                        "question_text": "string",
                                        "question_type": "string (MCQ/CODING/ESSAY/etc.)",
                                        "options": ["string"] (only for MCQ),
                                        "correct_answer": "string",
                                        "marks": number,
                                        "sample_input": "string" (for coding),
                                        "sample_output": "string" (for coding),
                                        "explanation": "string" (optional),
                                        "test_cases": [
                                            {{
                                                "input": "string",
                                                "output": "string"
                                            }}
                                        ] (for coding questions)
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
                    5. For coding questions, provide clear sample inputs/outputs and test cases
                    6. For MCQ questions, provide 4 options and mark the correct one
                    7. Include unique question_id for each question
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
                        
                        # Store test in MongoDB
                        test_record = {
                            "test_data": test_data,
                            "created_at": datetime.now(),
                            "role": st.session_state.test_data['role'],
                            "skills": st.session_state.test_data['skills_required'],
                            "job_description": st.session_state.test_data['job_description'],
                            "created_by": st.session_state.test_data['username'],
                            "user_id": st.session_state.test_data['user_id']
                        }
                        result = tests_collection.insert_one(test_record)
                        st.session_state.test_data['current_test_id'] = str(result.inserted_id)
                        
                        st.success("Test generated and stored successfully! Students can now take the test.")
                    except json.JSONDecodeError as e:
                        st.error(f"Failed to parse JSON response: {str(e)}")
                        st.text_area("Raw Response", generated_content, height=200)
                    except Exception as e:
                        st.error(f"Error generating test: {str(e)}")
                        st.write("Please try again or adjust your input parameters.")
    
    # Take Test Page (Student only)
    elif page == "Take Test" and st.session_state.test_data['user_type'] == 'student':
        st.header("📝 Take Recruitment Test")
        
        # Get available tests from MongoDB
        available_tests = list(tests_collection.find({}, {"test_data.test_title": 1, "role": 1, "_id": 1}))
        
        if not available_tests:
            st.warning("No tests available. Please check back later.")
        else:
            # Test selection
            test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']})" for test in available_tests}
            
            # Check if current_test_id is set
            if not st.session_state.test_data.get('current_test_id'):
                selected_test_id = st.selectbox("Select a test to take", options=list(test_options.keys()), 
                                            format_func=lambda x: test_options[x])
                
                # Check if student has already taken this test
                already_taken = responses_collection.count_documents({
                    "test_id": selected_test_id,
                    "student_email": st.session_state.test_data['student_email']
                }) > 0
                
                if already_taken:
                    st.warning("You have already taken this test. You cannot take it again.")
                elif st.button("Start Test"):
                    st.session_state.test_data['current_test_id'] = selected_test_id
                    st.session_state.test_data['test_submitted'] = False
                    st.session_state.test_data['start_time'] = datetime.now()
                    st.rerun()
            
            # If test is selected, show the test
            if st.session_state.test_data.get('current_test_id'):
                # Load test data from MongoDB
                test_record = tests_collection.find_one({"_id": ObjectId(st.session_state.test_data['current_test_id'])})
                
                if not test_record:
                    st.error("Test not found. Please select another test.")
                else:
                    test_data = test_record['test_data']
                    
                    # Initialize student_responses if not already done
                    if not st.session_state.test_data.get('student_responses'):
                        st.session_state.test_data['student_responses'] = {
                            'test_id': st.session_state.test_data['current_test_id'],
                            'student_name': st.session_state.test_data['student_name'],
                            'student_email': st.session_state.test_data['student_email'],
                            'start_time': datetime.now(),
                            'responses': {}
                        }
                    
                    # Check if test is submitted
                    if st.session_state.test_data.get('test_submitted', False):
                        st.success("Your test has been submitted successfully!")
                        if st.button("Take Another Test"):
                            st.session_state.test_data['current_test_id'] = None
                            st.session_state.test_data['test_submitted'] = False
                            st.session_state.test_data['student_responses'] = {}
                            st.rerun()
                    else:
                        # Show timer
                        start_time = st.session_state.test_data['student_responses'].get('start_time', datetime.now())
                        time_limit = test_data.get('total_duration', 60) * 60  # Convert to seconds
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        remaining_time = max(0, time_limit - elapsed_time)
                        
                        mins, secs = divmod(int(remaining_time), 60)
                        hours, mins = divmod(mins, 60)
                        
                        timer_style = "floating-timer"
                        if remaining_time < 300:  # 5 minutes warning
                            timer_style += " timer-warning"
                        
                        st.markdown(f"""
                        <div class="{timer_style}">
                            <p>Time Remaining</p>
                            <h3>{hours:02d}:{mins:02d}:{secs:02d}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Auto-submit when time is up
                        if remaining_time <= 0 and not st.session_state.test_data.get('test_submitted', False):
                            st.session_state.test_data['test_submitted'] = True
                            st.session_state.test_data['student_responses']['end_time'] = datetime.now()
                            
                            # Store responses in MongoDB
                            response_id = responses_collection.insert_one(st.session_state.test_data['student_responses']).inserted_id
                            st.warning("Time's up! Your test has been automatically submitted.")
                            st.rerun()
                        
                        # Display test
                        st.markdown(f"# {test_data['test_title']}")
                        st.markdown(f"Total Marks: {test_data['total_marks']} • Duration: {test_data['total_duration']} minutes")
                        
                        # Create a form for student responses
                        with st.form("test_response_form"):
                            for section_idx, section in enumerate(test_data['sections']):
                                st.markdown(f"## Section {section_idx+1}: {section['section_name']}")
                                st.markdown(section['section_instructions'])
                                
                                for question_idx, question in enumerate(section['questions']):
                                    with st.expander(f"Question {question_idx+1} ({question['marks']} marks)"):
                                        st.markdown(f"**{question['question_text']}**")
                                        
                                        # Different question types
                                        question_id = question['question_id']
                                        if question['question_type'].lower() == 'mcq':
                                            options = question.get('options', [])
                                            selected_option = st.radio(
                                                "Select your answer:",
                                                options=options,
                                                key=f"mcq_{question_id}",
                                                index=None
                                            )
                                            
                                            if selected_option:
                                                st.session_state.test_data['student_responses']['responses'][question_id] = {
                                                    'response': selected_option,
                                                    'question_type': question['question_type']
                                                }
                                        
                                        elif question['question_type'].lower() == 'coding':
                                            st.markdown("### Sample Input")
                                            st.code(question.get('sample_input', 'N/A'))
                                            
                                            st.markdown("### Sample Output")
                                            st.code(question.get('sample_output', 'N/A'))
                                            
                                            # Get existing response if any
                                            existing_code = st.session_state.test_data['student_responses'].get('responses', {}).get(question_id, {}).get('response', '')
                                            
                                            code_response = st.text_area(
                                                "Write your code here:",
                                                value=existing_code,
                                                height=300,
                                                key=f"code_{question_id}"
                                            )
                                            
                                            if code_response:
                                                st.session_state.test_data['student_responses']['responses'][question_id] = {
                                                    'response': code_response,
                                                    'question_type': question['question_type']
                                                }
                                        
                                        else:  # Essay or other types
                                            # Get existing response if any
                                            existing_text = st.session_state.test_data['student_responses'].get('responses', {}).get(question_id, {}).get('response', '')
                                            
                                            text_response = st.text_area(
                                                "Your answer:",
                                                value=existing_text,
                                                height=150,
                                                key=f"text_{question_id}"
                                            )
                                            
                                            if text_response:
                                                st.session_state.test_data['student_responses']['responses'][question_id] = {
                                                    'response': text_response,
                                                    'question_type': question['question_type']
                                                }
                            
                            # Submit button
                            submit_button = st.form_submit_button("Submit Test")
                            if submit_button:
                                # Update end time
                                st.session_state.test_data['student_responses']['end_time'] = datetime.now()
                                
                                # Check if all questions are answered
                                total_questions = sum(len(section['questions']) for section in test_data['sections'])
                                answered_questions = len(st.session_state.test_data['student_responses'].get('responses', {}))
                                
                                if answered_questions < total_questions:
                                    unanswered = total_questions - answered_questions
                                    if not st.session_state.get('confirm_submit', False):
                                        st.warning(f"You have {unanswered} unanswered question(s). Are you sure you want to submit?")
                                        if st.button("Confirm Submit"):
                                            st.session_state['confirm_submit'] = True
                                            st.rerun()
                                    else:
                                        # Store responses in MongoDB
                                        response_id = responses_collection.insert_one(st.session_state.test_data['student_responses']).inserted_id
                                        st.session_state.test_data['test_submitted'] = True
                                        st.success("Test submitted successfully!")
                                        st.rerun()
                                else:
                                    # Store responses in MongoDB
                                    response_id = responses_collection.insert_one(st.session_state.test_data['student_responses']).inserted_id
                                    st.session_state.test_data['test_submitted'] = True
                                    st.success("Test submitted successfully!")
                                    st.rerun()
    
    # View Results Page (Student only)
    elif page == "View Results" and st.session_state.test_data['user_type'] == 'student':
        st.header("📊 Your Test Results")
        
        # Get student's responses
        student_responses = list(responses_collection.find({
            "student_email": st.session_state.test_data['student_email']
        }).sort("end_time", -1))
        
        if not student_responses:
            st.info("You haven't taken any tests yet.")
        else:
            st.write(f"You have taken {len(student_responses)} test(s).")
            
            for idx, response in enumerate(student_responses):
                # Get test data
                test_record = tests_collection.find_one({"_id": ObjectId(response['test_id'])})
                if not test_record:
                    continue
                
                with st.expander(f"Test {idx+1}: {test_record['test_data']['test_title']} - {response['end_time'].strftime('%Y-%m-%d %H:%M')}"):
                    # Test info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Role:** {test_record.get('role', 'N/A')}")
                    with col2:
                        time_taken = (response['end_time'] - response['start_time']).total_seconds() / 60
                        st.markdown(f"**Time Taken:** {time_taken:.1f} minutes")
                    with col3:
                        if response.get('evaluated', False):
                            total_score = sum(eval_item.get('score', 0) for eval_item in response.get('evaluations', {}).values())
                            total_marks = test_record['test_data']['total_marks']
                            st.markdown(f"**Score:** {total_score}/{total_marks} ({total_score/total_marks*100:.1f}%)")
                        else:
                            st.markdown("**Status:** Awaiting evaluation")
                    
                    # Display detailed results if evaluated
                    if response.get('evaluated', False):
                        st.markdown("### Detailed Feedback")
                        
                        for section in test_record['test_data']['sections']:
                            for question in section['questions']:
                                question_id = question['question_id']
                                if question_id in response['responses'] and question_id in response.get('evaluations', {}):
                                    st.markdown(f"**Question:** {question['question_text']}")
                                    st.markdown(f"**Your Answer:** {response['responses'][question_id]['response']}")
                                    st.markdown(f"**Score:** {response['evaluations'][question_id]['score']}/{question['marks']}")
                                    st.markdown(f"**Feedback:** {response['evaluations'][question_id]['feedback']}")
                                    st.markdown("---")
                        
                        # Overall evaluation
                        if response.get('overall_feedback'):
                            st.markdown("### Overall Feedback")
                            st.write(response['overall_feedback'])
                    else:
                        st.info("Your test is still being evaluated. Check back later for results.")
    
    # View Tests Page (Teacher only)
    elif page == "View Tests" and st.session_state.test_data['user_type'] == 'teacher':
        st.header("📝 View Tests")
        
        # Get all tests created by this teacher
        all_tests = list(tests_collection.find({
            "user_id": st.session_state.test_data['user_id']
        }).sort("created_at", -1))
        
        if not all_tests:
            st.info("You haven't created any tests yet. Go to 'Generate Test' to create your first test.")
        else:
            # Test selection
            test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']}) - {test['created_at'].strftime('%Y-%m-%d')}" for test in all_tests}
            selected_test_id = st.selectbox("Select a test to view", options=list(test_options.keys()), 
                                        format_func=lambda x: test_options[x])
            
            # View selected test
            selected_test = tests_collection.find_one({"_id": ObjectId(selected_test_id)})
            if selected_test:
                test_data = selected_test['test_data']
                
                # Test info
                st.subheader(test_data['test_title'])
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Role:** {selected_test['role']}")
                with col2:
                    st.markdown(f"**Duration:** {test_data['total_duration']} minutes")
                with col3:
                    st.markdown(f"**Total Marks:** {test_data['total_marks']}")
                
                # Test content
                for section_idx, section in enumerate(test_data['sections']):
                    st.markdown(f"### Section {section_idx+1}: {section['section_name']}")
                    st.markdown(section['section_instructions'])
                    
                    for question_idx, question in enumerate(section['questions']):
                        with st.expander(f"Question {question_idx+1} ({question['marks']} marks)"):
                            st.markdown(f"**{question['question_text']}**")
                            
                            if question['question_type'].lower() == 'mcq':
                                st.markdown("**Options:**")
                                for option_idx, option in enumerate(question['options']):
                                    if option == question['correct_answer']:
                                        st.markdown(f"- **{option} ✓**")
                                    else:
                                        st.markdown(f"- {option}")
                            
                            elif question['question_type'].lower() == 'coding':
                                st.markdown("**Sample Input:**")
                                st.code(question.get('sample_input', 'N/A'))
                                
                                st.markdown("**Sample Output:**")
                                st.code(question.get('sample_output', 'N/A'))
                                
                                st.markdown("**Test Cases:**")
                                for tc_idx, test_case in enumerate(question.get('test_cases', [])):
                                    st.markdown(f"Test Case {tc_idx+1}:")
                                    st.code(f"Input: {test_case.get('input', 'N/A')}\nOutput: {test_case.get('output', 'N/A')}")
                            
                            if question.get('explanation'):
                                st.markdown("**Explanation:**")
                                st.markdown(question['explanation'])
                
                # Test responses
                st.markdown("### Student Responses")
                responses = list(responses_collection.find({"test_id": selected_test_id}).sort("end_time", -1))
                
                if not responses:
                    st.info("No students have taken this test yet.")
                else:
                    response_df = pd.DataFrame([{
                        "Student Name": resp['student_name'],
                        "Email": resp['student_email'],
                        "Submission Date": resp['end_time'].strftime('%Y-%m-%d %H:%M'),
                        "Status": "Evaluated" if resp.get('evaluated', False) else "Pending",
                        "Score": sum(eval_item.get('score', 0) for eval_item in resp.get('evaluations', {}).values()) if resp.get('evaluated', False) else "N/A"
                    } for resp in responses])
                    
                    st.dataframe(response_df)
                    
                    # Download responses
                    st.markdown(get_download_link(response_df, f"test_responses_{selected_test_id}.csv", "Download Responses CSV"), unsafe_allow_html=True)
    
    # Evaluate Responses Page (Teacher only)
    elif page == "Evaluate Responses" and st.session_state.test_data['user_type'] == 'teacher':
        st.header("📊 Evaluate Test Responses")
        
        # Get tests created by this teacher
        all_tests = list(tests_collection.find({
            "user_id": st.session_state.test_data['user_id']
        }).sort("created_at", -1))
        
        if not all_tests:
            st.info("You haven't created any tests yet.")
        else:
            # Test selection
            test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']}) - {test['created_at'].strftime('%Y-%m-%d')}" for test in all_tests}
            selected_test_id = st.selectbox("Select a test to evaluate", options=list(test_options.keys()), 
                                        format_func=lambda x: test_options[x])
            
            # Get unevaluated responses for this test
            unevaluated_responses = list(responses_collection.find({
                "test_id": selected_test_id,
                "evaluated": {"$ne": True}
            }).sort("end_time", -1))
            
            if not unevaluated_responses:
                # Get all responses if none are unevaluated
                responses = list(responses_collection.find({
                    "test_id": selected_test_id
                }).sort("end_time", -1))
                
                if not responses:
                    st.info("No students have taken this test yet.")
                else:
                    st.success("All responses for this test have been evaluated.")
                    
                    # Show evaluated responses
                    st.subheader("Evaluated Responses")
                    for resp_idx, response in enumerate(responses):
                        with st.expander(f"Response {resp_idx+1}: {response['student_name']} ({response['end_time'].strftime('%Y-%m-%d %H:%M')})"):
                            # Summary
                            total_score = sum(eval_item.get('score', 0) for eval_item in response.get('evaluations', {}).values())
                            test_record = tests_collection.find_one({"_id": ObjectId(selected_test_id)})
                            total_marks = test_record['test_data']['total_marks'] if test_record else 0
                            
                            st.markdown(f"**Score:** {total_score}/{total_marks} ({total_score/total_marks*100:.1f}%)")
                            
                            # Questions and responses
                            if test_record:
                                for section in test_record['test_data']['sections']:
                                    for question in section['questions']:
                                        question_id = question['question_id']
                                        if question_id in response['responses'] and question_id in response.get('evaluations', {}):
                                            st.markdown(f"**Question:** {question['question_text']}")
                                            st.markdown(f"**Student's Answer:** {response['responses'][question_id]['response']}")
                                            st.markdown(f"**Score:** {response['evaluations'][question_id]['score']}/{question['marks']}")
                                            st.markdown(f"**Feedback:** {response['evaluations'][question_id]['feedback']}")
                                            st.markdown("---")
            else:
                # Show unevaluated responses
                st.info(f"You have {len(unevaluated_responses)} unevaluated response(s) for this test.")
                
                if st.button("Evaluate All Responses"):
                    with st.spinner("Evaluating responses using AI... This may take a while."):
                        # Get test data
                        test_record = tests_collection.find_one({"_id": ObjectId(selected_test_id)})
                        if not test_record:
                            st.error("Test data not found.")
                        else:
                            # Process each response
                            for response in unevaluated_responses:
                                # Use LLM for evaluation
                                evaluations = evaluate_with_llm(response, test_record['test_data'])
                                
                                # Calculate total score
                                total_score = sum(eval_data['score'] for eval_data in evaluations.values())
                                
                                # Generate overall feedback
                                total_marks = test_record['test_data']['total_marks']
                                score_percentage = (total_score / total_marks) * 100
                                
                                # Find appropriate rubric level
                                rubric = test_record['test_data'].get('grading_rubric', {})
                                overall_feedback = ""
                                
                                for level, data in rubric.items():
                                    range_str = data.get('score_range', '')
                                    if '-' in range_str:
                                        try:
                                            lower, upper = map(float, range_str.replace('%', '').split('-'))
                                            if lower <= score_percentage <= upper:
                                                overall_feedback = data.get('description', '')
                                                break
                                        except:
                                            pass
                                
                                # Update response document
                                responses_collection.update_one(
                                    {"_id": response['_id']},
                                    {"$set": {
                                        "evaluations": evaluations,
                                        "score": total_score,
                                        "overall_feedback": overall_feedback,
                                        "evaluated": True,
                                        "evaluated_at": datetime.now(),
                                        "evaluated_by": st.session_state.test_data['username']
                                    }}
                                )
                            
                            st.success(f"Successfully evaluated {len(unevaluated_responses)} response(s).")
                            st.rerun()
    
    # Analytics Page (Teacher only)
    elif page == "Analytics" and st.session_state.test_data['user_type'] == 'teacher':
        st.header("📈 Test Analytics Dashboard")
        
        # Get all tests created by this teacher
        all_tests = list(tests_collection.find({
            "user_id": st.session_state.test_data['user_id']
        }).sort("created_at", -1))
        
        if not all_tests:
            st.info("You haven't created any tests yet.")
        else:
            # Test selection
            test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']}) - {test['created_at'].strftime('%Y-%m-%d')}" for test in all_tests}
            selected_test_id = st.selectbox("Select a test for analytics", options=list(test_options.keys()), 
                                            format_func=lambda x: test_options[x])
            
            # Get responses for this test
            responses = list(responses_collection.find({
                "test_id": selected_test_id,
                "evaluated": True
            }))
            
            if not responses:
                st.info("No evaluated responses available for this test.")
            else:
                st.success(f"Analyzing {len(responses)} evaluated response(s).")
                
                # Get test data
                test_record = tests_collection.find_one({"_id": ObjectId(selected_test_id)})
                test_data = test_record['test_data']
                total_marks = test_data['total_marks']
                
                # Overall statistics
                st.subheader("Overall Performance")
                
                # Calculate statistics
                scores = [sum(eval_item.get('score', 0) for eval_item in resp.get('evaluations', {}).values()) for resp in responses]
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                pass_count = sum(1 for score in scores if score >= total_marks * 0.4)  # Assuming 40% is pass
                pass_rate = pass_count / len(scores) * 100
                
                # Display stats
                cols = st.columns(5)
                with cols[0]:
                    st.markdown("""
                    <div class="dashboard-card">
                        <p class="card-title">Avg. Score</p>
                        <p class="card-value" style="color: #4CAF50;">{:.1f}%</p>
                    </div>
                    """.format(avg_score / total_marks * 100), unsafe_allow_html=True)
                
                with cols[1]:
                    st.markdown("""
                    <div class="dashboard-card">
                        <p class="card-title">Highest Score</p>
                        <p class="card-value" style="color: #2196F3;">{:.1f}%</p>
                    </div>
                    """.format(max_score / total_marks * 100), unsafe_allow_html=True)
                
                with cols[2]:
                    st.markdown("""
                    <div class="dashboard-card">
                        <p class="card-title">Lowest Score</p>
                        <p class="card-value" style="color: #F44336;">{:.1f}%</p>
                    </div>
                    """.format(min_score / total_marks * 100), unsafe_allow_html=True)
                
                with cols[3]:
                    st.markdown("""
                    <div class="dashboard-card">
                        <p class="card-title">Pass Rate</p>
                        <p class="card-value" style="color: #FF9800;">{:.1f}%</p>
                    </div>
                    """.format(pass_rate), unsafe_allow_html=True)
                
                with cols[4]:
                    st.markdown("""
                    <div class="dashboard-card">
                        <p class="card-title">Responses</p>
                        <p class="card-value" style="color: #9C27B0;">{}</p>
                    </div>
                    """.format(len(responses)), unsafe_allow_html=True)
                
                # Score distribution
                st.subheader("Score Distribution")
                
                # Create histogram
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.hist(scores, bins=10, color='#4CAF50', alpha=0.7)
                ax.set_xlabel('Score')
                ax.set_ylabel('Number of Students')
                ax.set_title('Score Distribution')
                ax.axvline(avg_score, color='red', linestyle='dashed', linewidth=1, label=f'Mean: {avg_score:.1f}')
                ax.legend()
                
                st.pyplot(fig)
                
                # Section-wise analysis
                st.subheader("Section-wise Performance")
                
                # Organize questions by section
                section_questions = {}
                for idx, section in enumerate(test_data['sections']):
                    section_name = section['section_name']
                    section_questions[section_name] = []
                    for question in section['questions']:
                        section_questions[section_name].append(question['question_id'])
                
                # Calculate section scores
                section_scores = {}
                for section_name, question_ids in section_questions.items():
                    section_scores[section_name] = []
                    for resp in responses:
                        if 'evaluations' in resp:
                            section_total = 0
                            for q_id in question_ids:
                                if q_id in resp['evaluations']:
                                    section_total += resp['evaluations'][q_id]['score']
                            section_scores[section_name].append(section_total)
                
                # Calculate section averages
                section_avgs = {name: sum(scores)/len(scores) if scores else 0 for name, scores in section_scores.items()}
                
                # Create bar chart
                fig, ax = plt.subplots(figsize=(10, 6))
                sections = list(section_avgs.keys())
                avgs = list(section_avgs.values())
                
                # Get section max scores
                section_maxes = {}
                for section in test_data['sections']:
                    section_name = section['section_name']
                    section_maxes[section_name] = section['total_marks']
                
                max_scores = [section_maxes[name] for name in sections]
                
                # Calculate percentages
                percentages = [avg/max_score*100 for avg, max_score in zip(avgs, max_scores)]
                
                ax.bar(sections, percentages, color='#2196F3', alpha=0.7)
                ax.set_xlabel('Sections')
                ax.set_ylabel('Average Score (%)')
                ax.set_title('Section-wise Performance')
                plt.xticks(rotation=45, ha='right')
                
                st.pyplot(fig)
                
                # Question-wise analysis
                st.subheader("Question-wise Performance")
                
                # Calculate question scores
                question_data = []
                for section in test_data['sections']:
                    section_name = section['section_name']
                    for question in section['questions']:
                        q_id = question['question_id']
                        q_type = question['question_type']
                        q_marks = question['marks']
                        
                        correct_count = 0
                        total_score = 0
                        for resp in responses:
                            if 'evaluations' in resp and q_id in resp['evaluations']:
                                score = resp['evaluations'][q_id]['score']
                                total_score += score
                                if score == q_marks:  # Full marks = correct
                                    correct_count += 1
                        
                        avg_score = total_score / len(responses) if responses else 0
                        difficulty = 1 - (avg_score / q_marks) if q_marks > 0 else 0  # Higher value = more difficult
                        
                        question_data.append({
                            'Question': f"Q{len(question_data)+1}",
                            'Section': section_name,
                            'Type': q_type,
                            'Avg Score': avg_score,
                            'Max Score': q_marks,
                            'Percentage': (avg_score / q_marks * 100) if q_marks > 0 else 0,
                            'Correct Count': correct_count,
                            'Correct %': (correct_count / len(responses) * 100) if responses else 0,
                            'Difficulty': difficulty
                        })
                
                # Convert to DataFrame
                q_df = pd.DataFrame(question_data)
                
                # Display questions table
                st.dataframe(q_df)
                
                # Top difficult questions
                st.subheader("Most Difficult Questions")
                difficult_qs = q_df.sort_values('Difficulty', ascending=False).head(5)

                fig, ax = plt.subplots(figsize=(10, 6))
                ax.barh(difficult_qs['Question'], difficult_qs['Difficulty'], color='#F44336', alpha=0.7)
                ax.set_xlabel('Difficulty Index (Higher = More Difficult)')
                ax.set_ylabel('Question')
                ax.set_title('Most Difficult Questions')
                
                st.pyplot(fig)
                
                # Time analysis
                st.subheader("Time Analysis")
                
                # Calculate time taken by each student
                time_data = []
                for resp in responses:
                    if 'start_time' in resp and 'end_time' in resp:
                        time_taken = (resp['end_time'] - resp['start_time']).total_seconds() / 60  # minutes
                        total_score = sum(eval_item.get('score', 0) for eval_item in resp.get('evaluations', {}).values())
                        score_percentage = (total_score / total_marks) * 100 if total_marks > 0 else 0
                        
                        time_data.append({
                            'Student': resp['student_name'],
                            'Time (min)': time_taken,
                            'Score (%)': score_percentage
                        })
                
                # Convert to DataFrame
                time_df = pd.DataFrame(time_data)
                
                # Scatter plot of time vs score
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.scatter(time_df['Time (min)'], time_df['Score (%)'], color='#4CAF50', alpha=0.7)
                ax.set_xlabel('Time Taken (minutes)')
                ax.set_ylabel('Score (%)')
                ax.set_title('Correlation between Time Taken and Score')
                
                # Add trendline
                if len(time_df) > 1:  # Need at least 2 points for regression
                    x = time_df['Time (min)']
                    y = time_df['Score (%)']
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    ax.plot(x, p(x), "r--", alpha=0.7)
                
                st.pyplot(fig)

                st.subheader("Export Data")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Generate response report
                    response_report = create_pdf_report(test_data, responses)
                    st.markdown(get_download_link(response_report, f"test_report_{selected_test_id}.csv", 
                                                "Download Response Report"), unsafe_allow_html=True)
                
                with col2:
                    # Export question analysis
                    st.markdown(get_download_link(q_df, f"question_analysis_{selected_test_id}.csv", 
                                                "Download Question Analysis"), unsafe_allow_html=True)
                
                # Recommendations based on data
                st.subheader("AI Recommendations")
                
                # Prepare data for AI analysis
                prompt = f"""
                Analyze the following test performance data and provide recommendations for improvement:
                
                Test Title: {test_data['test_title']}
                Total Student Responses: {len(responses)}
                Average Score: {avg_score:.1f}/{total_marks} ({avg_score/total_marks*100:.1f}%)
                Pass Rate: {pass_rate:.1f}%
                
                Most Difficult Questions:
                {difficult_qs[['Question', 'Section', 'Type', 'Difficulty', 'Correct %']].to_string(index=False)}
                
                Section Performance:
                {pd.DataFrame({'Section': list(section_avgs.keys()), 'Average Score': list(section_avgs.values())}).to_string(index=False)}
                
                Please provide 3-5 actionable recommendations for:
                1. Improving the test quality
                2. Enhancing student performance
                3. Focusing on key areas for improvement
                
                Format your response in bullet points.
                """
                
                with st.spinner("Generating AI recommendations..."):
                    try:
                        recommendation_response = model.generate_content(prompt)
                        recommendations = recommendation_response.text
                        st.markdown(recommendations)
                    except Exception as e:
                        st.error(f"Error generating recommendations: {str(e)}")

# Add a feature to export test details for sharing
def export_test_code(test_data):
    """Generate a shareable code for a test"""
    # Create a simplified version of the test for sharing
    shareable_test = {
        "test_title": test_data['test_title'],
        "total_duration": test_data['total_duration'],
        "total_marks": test_data['total_marks'],
        "sections": test_data['sections']
    }
    
    # Convert to JSON and encode in base64
    test_json = json.dumps(shareable_test)
    test_code = base64.b64encode(test_json.encode()).decode()
    
    # Return first 10 characters as a preview
    return test_code, test_code[:10] + "..."

# Add a feature to import tests from codes
def import_test_from_code(test_code):
    """Import a test from a shareable code"""
    try:
        # Decode the base64 code
        test_json = base64.b64decode(test_code).decode()
        test_data = json.loads(test_json)
        
        # Validate the test structure
        required_fields = ["test_title", "total_duration", "total_marks", "sections"]
        for field in required_fields:
            if field not in test_data:
                return None, f"Invalid test format: missing '{field}'"
        
        return test_data, "Test imported successfully"
    except Exception as e:
        return None, f"Error importing test: {str(e)}"

# Function to generate test report PDF
def generate_test_report_pdf(test_data, responses):
    """Generate a comprehensive PDF report for a test"""
    # This would typically use a PDF generation library
    # For simplicity, we'll create a buffer and return it
    buffer = io.BytesIO()
    
    plt.figure(figsize=(8.5, 11))
    plt.text(0.5, 0.98, f"Test Report: {test_data['test_title']}", 
             horizontalalignment='center', fontsize=16, fontweight='bold')
    
    # Add summary statistics
    scores = [sum(eval_item.get('score', 0) for eval_item in resp.get('evaluations', {}).values()) for resp in responses]
    avg_score = sum(scores) / len(scores) if scores else 0
    total_marks = test_data['total_marks']
    
    plt.text(0.1, 0.9, f"Total Responses: {len(responses)}", fontsize=12)
    plt.text(0.1, 0.87, f"Average Score: {avg_score:.1f}/{total_marks} ({avg_score/total_marks*100:.1f}%)", fontsize=12)
    
    # Add a score distribution histogram
    if scores:
        ax = plt.axes([0.1, 0.55, 0.8, 0.25])
        ax.hist(scores, bins=10, color='#4CAF50', alpha=0.7)
        ax.set_xlabel('Score')
        ax.set_ylabel('Number of Students')
        ax.set_title('Score Distribution')
    
    # Add a table of top students
    if responses:
        top_students = sorted(responses, 
                           key=lambda x: sum(eval_item.get('score', 0) for eval_item in x.get('evaluations', {}).values()),
                           reverse=True)[:5]
        
        student_names = [s['student_name'] for s in top_students]
        student_scores = [sum(eval_item.get('score', 0) for eval_item in s.get('evaluations', {}).values()) for s in top_students]
        
        ax = plt.axes([0.1, 0.2, 0.8, 0.25])
        ax.axis('tight')
        ax.axis('off')
        ax.table(cellText=[[n, f"{s}/{total_marks} ({s/total_marks*100:.1f}%)"] for n, s in zip(student_names, student_scores)],
               colLabels=["Student Name", "Score"],
               loc='center')
        ax.set_title('Top Performing Students')
    
    plt.savefig(buffer, format='pdf')
    plt.close()
    
    buffer.seek(0)
    return buffer

# Add a feature to provide AI-powered student performance analysis
def analyze_student_performance(student_responses, test_data):
    """Use AI to analyze a student's performance and provide feedback"""
    # Calculate overall performance
    total_score = sum(eval_item.get('score', 0) for eval_item in student_responses.get('evaluations', {}).values())
    total_marks = test_data['total_marks']
    score_percentage = (total_score / total_marks) * 100 if total_marks > 0 else 0
    
    # Organize responses by section
    section_performance = {}
    for section in test_data['sections']:
        section_name = section['section_name']
        section_score = 0
        section_total = 0
        
        for question in section['questions']:
            q_id = question['question_id']
            q_marks = question['marks']
            section_total += q_marks
            
            if q_id in student_responses.get('evaluations', {}):
                section_score += student_responses['evaluations'][q_id]['score']
        
        if section_total > 0:
            section_performance[section_name] = {
                'score': section_score,
                'total': section_total,
                'percentage': (section_score / section_total) * 100
            }
    
    # Identify strengths and weaknesses
    strengths = [s for s, p in section_performance.items() if p['percentage'] >= 70]
    weaknesses = [s for s, p in section_performance.items() if p['percentage'] < 50]
    
    # Prepare data for AI analysis
    prompt = f"""
    Analyze the following student performance data and provide personalized feedback:
    
    Overall Score: {total_score}/{total_marks} ({score_percentage:.1f}%)
    
    Section Performance:
    {', '.join([f"{s}: {p['score']}/{p['total']} ({p['percentage']:.1f}%)" for s, p in section_performance.items()])}
    
    Strengths: {', '.join(strengths) if strengths else 'None identified'}
    Weaknesses: {', '.join(weaknesses) if weaknesses else 'None identified'}
    
    Please provide:
    1. A brief overall assessment of the student's performance
    2. Specific strengths identified from the data
    3. Areas that need improvement
    4. 3-5 personalized recommendations for the student to improve their skills
    
    Format your response in paragraphs with clear headings.
    """
    
    try:
        analysis_response = model.generate_content(prompt)
        return analysis_response.text
    except Exception as e:
        return f"Error generating performance analysis: {str(e)}"

# Add notification system
def send_notification(recipient_email, subject, message):
    """Send notification to users"""
    # In a real application, this would connect to an email service
    # For now, we'll just log the notification
    st.write(f"Notification sent to {recipient_email}: {subject}")
    st.write(f"Message: {message}")
    return True

# Add batch evaluation feature
def batch_evaluate_responses(test_id):
    """Evaluate all pending responses for a test"""
    # Get test data
    test_record = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test_record:
        return False, "Test not found"
    
    # Get unevaluated responses
    unevaluated_responses = list(responses_collection.find({
        "test_id": test_id,
        "evaluated": {"$ne": True}
    }))
    
    if not unevaluated_responses:
        return False, "No unevaluated responses found"
    
    # Process each response
    success_count = 0
    error_count = 0
    
    for response in unevaluated_responses:
        try:
            # Use LLM for evaluation
            evaluations = evaluate_with_llm(response, test_record['test_data'])
            
            # Calculate total score
            total_score = sum(eval_data['score'] for eval_data in evaluations.values())
            
            # Update response document
            responses_collection.update_one(
                {"_id": response['_id']},
                {"$set": {
                    "evaluations": evaluations,
                    "score": total_score,
                    "evaluated": True,
                    "evaluated_at": datetime.now()
                }}
            )
            
            success_count += 1
        except Exception as e:
            error_count += 1
    
    return True, f"Evaluated {success_count} responses successfully. {error_count} failed."

# Add a feature to generate certificates for students
def generate_certificate(student_name, test_title, score, total_marks, date):
    """Generate a certificate for student completion"""
    # Create a simple certificate design
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    
    # Certificate border
    rect = plt.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=2, edgecolor='gold', facecolor='none', transform=fig.transFigure)
    fig.patches.extend([rect])
    
    # Title
    plt.text(0.5, 0.85, "CERTIFICATE OF COMPLETION", transform=fig.transFigure, 
             fontsize=24, fontweight='bold', ha='center')
    
    # Content
    plt.text(0.5, 0.7, f"This certifies that", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.5, 0.65, f"{student_name}", transform=fig.transFigure, fontsize=20, fontweight='bold', ha='center')
    plt.text(0.5, 0.58, f"has successfully completed the assessment", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.5, 0.53, f"{test_title}", transform=fig.transFigure, fontsize=18, fontweight='bold', ha='center')
    plt.text(0.5, 0.45, f"with a score of {score}/{total_marks} ({score/total_marks*100:.1f}%)", 
             transform=fig.transFigure, fontsize=16, ha='center')
    
    # Date
    plt.text(0.5, 0.35, f"Date: {date.strftime('%B %d, %Y')}", transform=fig.transFigure, fontsize=14, ha='center')
    
    # Signature
    plt.text(0.25, 0.22, "________________", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.25, 0.18, "Examiner", transform=fig.transFigure, fontsize=14, ha='center')
    
    plt.text(0.75, 0.22, "________________", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.75, 0.18, "Institution", transform=fig.transFigure, fontsize=14, ha='center')
    
    # Convert to bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300)
    plt.close()
    
    buffer.seek(0)
    return buffer


def analyze_student_performance(student_responses, test_data):
    """Use AI to analyze a student's performance and provide feedback"""
    # Calculate overall performance
    total_score = sum(eval_item.get('score', 0) for eval_item in student_responses.get('evaluations', {}).values())
    total_marks = test_data['total_marks']
    score_percentage = (total_score / total_marks) * 100 if total_marks > 0 else 0
    
    # Organize responses by section
    section_performance = {}
    for section in test_data['sections']:
        section_name = section['section_name']
        section_score = 0
        section_total = 0
        
        for question in section['questions']:
            q_id = question['question_id']
            q_marks = question['marks']
            section_total += q_marks
            
            if q_id in student_responses.get('evaluations', {}):
                section_score += student_responses['evaluations'][q_id]['score']
        
        if section_total > 0:
            section_performance[section_name] = {
                'score': section_score,
                'total': section_total,
                'percentage': (section_score / section_total) * 100
            }
    
    # Identify strengths and weaknesses
    strengths = [s for s, p in section_performance.items() if p['percentage'] >= 70]
    weaknesses = [s for s, p in section_performance.items() if p['percentage'] < 50]
    
    # Prepare data for AI analysis
    prompt = f"""
    Analyze the following student performance data and provide personalized feedback:
    
    Overall Score: {total_score}/{total_marks} ({score_percentage:.1f}%)
    
    Section Performance:
    {', '.join([f"{s}: {p['score']}/{p['total']} ({p['percentage']:.1f}%)" for s, p in section_performance.items()])}
    
    Strengths: {', '.join(strengths) if strengths else 'None identified'}
    Weaknesses: {', '.join(weaknesses) if weaknesses else 'None identified'}
    
    Please provide:
    1. A brief overall assessment of the student's performance
    2. Specific strengths identified from the data
    3. Areas that need improvement
    4. 3-5 personalized recommendations for the student to improve their skills
    
    Format your response in paragraphs with clear headings.
    """
    
    try:
        analysis_response = model.generate_content(prompt)
        return analysis_response.text
    except Exception as e:
        return f"Error generating performance analysis: {str(e)}"

# Add notification system
def send_notification(recipient_email, subject, message):
    """Send notification to users"""
    # In a real application, this would connect to an email service
    # For now, we'll just log the notification
    st.write(f"Notification sent to {recipient_email}: {subject}")
    st.write(f"Message: {message}")
    return True

# Add batch evaluation feature
def batch_evaluate_responses(test_id):
    """Evaluate all pending responses for a test"""
    # Get test data
    test_record = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test_record:
        return False, "Test not found"
    
    # Get unevaluated responses
    unevaluated_responses = list(responses_collection.find({
        "test_id": test_id,
        "evaluated": {"$ne": True}
    }))
    
    if not unevaluated_responses:
        return False, "No unevaluated responses found"
    
    # Process each response
    success_count = 0
    error_count = 0
    
    for response in unevaluated_responses:
        try:
            # Use LLM for evaluation
            evaluations = evaluate_with_llm(response, test_record['test_data'])
            
            # Calculate total score
            total_score = sum(eval_data['score'] for eval_data in evaluations.values())
            
            # Update response document
            responses_collection.update_one(
                {"_id": response['_id']},
                {"$set": {
                    "evaluations": evaluations,
                    "score": total_score,
                    "evaluated": True,
                    "evaluated_at": datetime.now()
                }}
            )
            
            success_count += 1
        except Exception as e:
            error_count += 1
    
    return True, f"Evaluated {success_count} responses successfully. {error_count} failed."

# Add a feature to generate certificates for students
def generate_certificate(student_name, test_title, score, total_marks, date):
    """Generate a certificate for student completion"""
    # Create a simple certificate design
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    
    # Certificate border
    rect = plt.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=2, edgecolor='gold', facecolor='none', transform=fig.transFigure)
    fig.patches.extend([rect])
    
    # Title
    plt.text(0.5, 0.85, "CERTIFICATE OF COMPLETION", transform=fig.transFigure, 
             fontsize=24, fontweight='bold', ha='center')
    
    # Content
    plt.text(0.5, 0.7, f"This certifies that", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.5, 0.65, f"{student_name}", transform=fig.transFigure, fontsize=20, fontweight='bold', ha='center')
    plt.text(0.5, 0.58, f"has successfully completed the assessment", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.5, 0.53, f"{test_title}", transform=fig.transFigure, fontsize=18, fontweight='bold', ha='center')
    plt.text(0.5, 0.45, f"with a score of {score}/{total_marks} ({score/total_marks*100:.1f}%)", 
             transform=fig.transFigure, fontsize=16, ha='center')
    
    # Date
    plt.text(0.5, 0.35, f"Date: {date.strftime('%B %d, %Y')}", transform=fig.transFigure, fontsize=14, ha='center')
    
    # Signature
    plt.text(0.25, 0.22, "________________", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.25, 0.18, "Examiner", transform=fig.transFigure, fontsize=14, ha='center')
    
    plt.text(0.75, 0.22, "________________", transform=fig.transFigure, fontsize=14, ha='center')
    plt.text(0.75, 0.18, "Institution", transform=fig.transFigure, fontsize=14, ha='center')
    
    # Convert to bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300)
    plt.close()
    
    buffer.seek(0)
    return buffer

# Add an error logging function
def log_error(error_type, error_message, user_id=None):
    """Log errors to help with troubleshooting"""
    error_log = {
        "error_type": error_type,
        "error_message": str(error_message),
        "timestamp": datetime.now(),
        "user_id": user_id
    }
    
    # In a real application, this would log to a database or file
    print(f"ERROR: {error_type} - {error_message}")
    return error_log

# Add search functionality for teachers
def search_responses(search_query, user_id):
    """Search through responses based on student name or email"""
    # Get all tests created by this teacher
    teacher_tests = [str(test['_id']) for test in tests_collection.find({"user_id": user_id})]
    
    # Search responses
    search_results = list(responses_collection.find({
        "$and": [
            {"test_id": {"$in": teacher_tests}},
            {"$or": [
                {"student_name": {"$regex": search_query, "$options": "i"}},
                {"student_email": {"$regex": search_query, "$options": "i"}}
            ]}
        ]
    }).sort("end_time", -1))
    
    return search_results

# Main loop additions for the app - add these to enhance the existing functionality
if 'advanced_features' not in st.session_state:
    st.session_state.advanced_features = {
        'enable_ai_analysis': True,
        'enable_peer_comparison': True,
        'enable_certificates': True,
        'dark_mode': False
    }

# Add these features to the teacher dashboard
if page == "Dashboard" and st.session_state.test_data['user_type'] == 'teacher':
    # Add quick search 
    st.sidebar.subheader("Quick Search")
    search_query = st.sidebar.text_input("Search students", "")
    if search_query:
        search_results = search_responses(search_query, st.session_state.test_data['user_id'])
        st.sidebar.write(f"Found {len(search_results)} result(s)")
        for result in search_results[:5]:  # Show top 5 results
            st.sidebar.markdown(f"**{result['student_name']}** - {result['student_email']}")
    
    # Add settings
    st.sidebar.subheader("Settings")
    st.session_state.advanced_features['enable_ai_analysis'] = st.sidebar.checkbox(
        "Enable AI Analysis", value=st.session_state.advanced_features['enable_ai_analysis'])
    st.session_state.advanced_features['enable_certificates'] = st.sidebar.checkbox(
        "Enable Certificates", value=st.session_state.advanced_features['enable_certificates'])
    st.session_state.advanced_features['dark_mode'] = st.sidebar.checkbox(
        "Dark Mode", value=st.session_state.advanced_features['dark_mode'])
    
    # Apply dark mode if enabled
    if st.session_state.advanced_features['dark_mode']:
        st.markdown("""
        <style>
        .main {background-color: #121212 !important;}
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {background-color: #1e1e1e; color: #ffffff;}
        .stButton>button {background-color: #388e3c; color: white;}
        .stSelectbox>div>div>select {background-color: #1e1e1e; color: #ffffff;}
        h1, h2, h3, h4, h5, h6, .stMarkdown, p {color: #ffffff !important;}
        .section-box, .dashboard-card {background-color: #1e1e1e; color: #ffffff;}
        </style>
        """, unsafe_allow_html=True)

# Add certificate generation for students
if page == "View Results" and st.session_state.test_data['user_type'] == 'student':
    # Add certificate download option for evaluated tests
    for idx, response in enumerate(student_responses):
        if response.get('evaluated', False):
            test_record = tests_collection.find_one({"_id": ObjectId(response['test_id'])})
            if test_record and st.session_state.advanced_features['enable_certificates']:
                total_score = sum(eval_item.get('score', 0) for eval_item in response.get('evaluations', {}).values())
                total_marks = test_record['test_data']['total_marks']
                
                # Check if score is passing (e.g., 40% or higher)
                if total_score / total_marks >= 0.4:
                    if st.button(f"Download Certificate for {test_record['test_data']['test_title']}", key=f"cert_{idx}"):
                        certificate = generate_certificate(
                            st.session_state.test_data['student_name'],
                            test_record['test_data']['test_title'],
                            total_score,
                            total_marks,
                            response['end_time']
                        )
                        
                        # Convert to base64 for download
                        b64 = base64.b64encode(certificate.getvalue()).decode()
                        href = f'<a href="data:image/png;base64,{b64}" download="certificate_{response["test_id"]}.png">Click here to download your certificate</a>'
                        st.markdown(href, unsafe_allow_html=True)

# Add batch operations for teachers
if page == "Evaluate Responses" and st.session_state.test_data['user_type'] == 'teacher':
    st.sidebar.subheader("Batch Operations")
    if st.sidebar.button("Evaluate All Pending Tests"):
        # Get all tests by this teacher
        all_tests = list(tests_collection.find({
            "user_id": st.session_state.test_data['user_id']
        }))
        
        if not all_tests:
            st.sidebar.info("No tests available.")
        else:
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            for i, test in enumerate(all_tests):
                test_id = str(test['_id'])
                status_text.text(f"Processing test {i+1}/{len(all_tests)}: {test['test_data']['test_title']}")
                
                success, message = batch_evaluate_responses(test_id)
                if success:
                    st.sidebar.success(message)
                else:
                    st.sidebar.warning(message)
                
                progress_bar.progress((i + 1) / len(all_tests))
            
            status_text.text("Batch evaluation complete!")

# Add test import/export features
if page == "Generate Test" and st.session_state.test_data['user_type'] == 'teacher':
    st.sidebar.subheader("Import/Export Test")
    
    # Export feature
    if st.session_state.test_data.get('generated_test'):
        test_code, preview = export_test_code(st.session_state.test_data['generated_test'])
        st.sidebar.text_input("Test Code (Copy to share)", preview, disabled=True)
        if st.sidebar.button("Copy Full Code"):
            st.sidebar.code(test_code)
            st.sidebar.success("Code copied! Share this with other teachers.")
    
    # Import feature
    import_code = st.sidebar.text_input("Import Test Code")
    if import_code and st.sidebar.button("Import Test"):
        imported_test, message = import_test_from_code(import_code)
        if imported_test:
            st.sidebar.success(message)
            
            # Store imported test
            test_record = {
                "test_data": imported_test,
                "created_at": datetime.now(),
                "role": imported_test.get('test_title', 'Imported Test'),
                "skills": "Imported",
                "job_description": "Imported test",
                "created_by": st.session_state.test_data['username'],
                "user_id": st.session_state.test_data['user_id'],
                "imported": True
            }
            result = tests_collection.insert_one(test_record)
            st.sidebar.success(f"Test imported with ID: {result.inserted_id}")
        else:
            st.sidebar.error(message)

# Main app execution continues here...
if __name__ == "__main__":
    pass  # App is run by Streamlit
