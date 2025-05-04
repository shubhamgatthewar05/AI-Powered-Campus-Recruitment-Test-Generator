import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

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
        'student_email': ''
    }

# App header
st.title("🏛️ Campus Recruitment Test Generator")
st.markdown("---")

# User type selection
if st.session_state.test_data['user_type'] is None:
    st.subheader("Select User Type")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Teacher/Admin"):
            st.session_state.test_data['user_type'] = 'teacher'
            st.rerun()
    with col2:
        if st.button("Student"):
            st.session_state.test_data['user_type'] = 'student'
            st.rerun()

# Page navigation based on user type
if st.session_state.test_data['user_type'] == 'teacher':
    pages = ["Input Details", "Generate Test", "View Tests", "Evaluate Responses"]
    page = st.sidebar.radio("Navigation", pages)
elif st.session_state.test_data['user_type'] == 'student':
    pages = ["Take Test", "View Results"]
    page = st.sidebar.radio("Navigation", pages)
else:
    st.stop()

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

# Input Details Page (Teacher only)
if page == "Input Details" and st.session_state.test_data['user_type'] == 'teacher':
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
                        "created_by": "teacher"  # In a real app, you'd store the actual user ID
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
    
    # Student information form
    if not st.session_state.test_data.get('student_name'):
        with st.form("student_info_form"):
            st.session_state.test_data['student_name'] = st.text_input("Your Name")
            st.session_state.test_data['student_email'] = st.text_input("Your Email")
            
            submitted = st.form_submit_button("Continue")
            if submitted:
                if not st.session_state.test_data['student_name'] or not st.session_state.test_data['student_email']:
                    st.warning("Please enter both your name and email")
                else:
                    st.rerun()
    
    else:
        # Get available tests from MongoDB
        available_tests = list(tests_collection.find({}, {"test_data.test_title": 1, "role": 1, "_id": 1}))
        
        if not available_tests:
            st.warning("No tests available. Please check back later.")
        else:
            # Test selection
            test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']})" for test in available_tests}
            selected_test_id = st.selectbox("Select a test to take", options=list(test_options.keys()), 
                                          format_func=lambda x: test_options[x])
            
            if st.button("Start Test"):
                st.session_state.test_data['current_test_id'] = selected_test_id
                st.session_state.test_data['test_submitted'] = False
                st.session_state.test_data['student_responses'] = {}
                st.rerun()
            
            if st.session_state.test_data.get('current_test_id'):
                # Load the selected test
                test_record = tests_collection.find_one({"_id": ObjectId(st.session_state.test_data['current_test_id'])})
                test_data = test_record['test_data']
                
                if not st.session_state.test_data['test_submitted']:
                    with st.form("test_response_form"):
                        st.markdown(f"## {test_data['test_title']}")
                        st.markdown(f"**Total Duration:** {test_data['total_duration']} minutes | **Total Marks:** {test_data['total_marks']}")
                        
                        # Initialize responses if not already done
                        if not st.session_state.test_data['student_responses']:
                            st.session_state.test_data['student_responses'] = {
                                "test_id": st.session_state.test_data['current_test_id'],
                                "student_name": st.session_state.test_data['student_name'],
                                "student_email": st.session_state.test_data['student_email'],
                                "responses": {},
                                "start_time": datetime.now(),
                                "end_time": None,
                                "score": None,
                                "evaluated": False
                            }
                        
                        # Display each section
                        for section in test_data['sections']:
                            st.markdown(f"### {section['section_name']} (Total Marks: {section['total_marks']})")
                            st.markdown(f"*{section['section_instructions']}*")
                            
                            # Display each question
                            for question in section['questions']:
                                question_id = question['question_id']
                                
                                # Initialize response if not exists
                                if question_id not in st.session_state.test_data['student_responses']['responses']:
                                    st.session_state.test_data['student_responses']['responses'][question_id] = {
                                        "question_type": question['question_type'],
                                        "response": "",
                                        "marks": question['marks'],
                                        "evaluated": False
                                    }
                                
                                st.markdown(f"**{question['question_text']}** [{question['marks']} mark(s)]")
                                
                                # MCQ Question
                                if question['question_type'].lower() == 'mcq':
                                    options = question.get('options', [])
                                    selected_option = st.radio(
                                        "Select your answer:",
                                        options,
                                        key=f"mcq_{question_id}",
                                        index=None
                                    )
                                    st.session_state.test_data['student_responses']['responses'][question_id]['response'] = selected_option
                                
                                # Coding Question
                                elif question['question_type'].lower() == 'coding':
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown("**Sample Input:**")
                                        st.code(question.get('sample_input', 'Not provided'))
                                    with col2:
                                        st.markdown("**Sample Output:**")
                                        st.code(question.get('sample_output', 'Not provided'))
                                    
                                    # Code editor
                                    code = st.text_area(
                                        "Write your code here:",
                                        height=300,
                                        key=f"code_{question_id}",
                                        value=st.session_state.test_data['student_responses']['responses'][question_id]['response']
                                    )
                                    st.session_state.test_data['student_responses']['responses'][question_id]['response'] = code
                                
                                # Other question types
                                else:
                                    answer = st.text_area(
                                        "Your answer:",
                                        height=100,
                                        key=f"text_{question_id}",
                                        value=st.session_state.test_data['student_responses']['responses'][question_id]['response']
                                    )
                                    st.session_state.test_data['student_responses']['responses'][question_id]['response'] = answer
                                
                                st.markdown("---")
                        
                        # Submit button
                        submitted = st.form_submit_button("Submit Test")
                        if submitted:
                            st.session_state.test_data['student_responses']['end_time'] = datetime.now()
                            st.session_state.test_data['test_submitted'] = True
                            
                            # Store responses in MongoDB
                            responses_collection.insert_one(st.session_state.test_data['student_responses'])
                            st.rerun()
                
                else:
                    st.success("Test submitted successfully!")
                    st.balloons()
                    st.markdown("Your responses have been recorded. The teacher will evaluate your test and you can view the results later.")

# View Tests Page (Teacher only)
elif page == "View Tests" and st.session_state.test_data['user_type'] == 'teacher':
    st.header("📊 View Generated Tests")
    
    # Get all tests from MongoDB
    all_tests = list(tests_collection.find({}))
    
    if not all_tests:
        st.warning("No tests available. Please generate a test first.")
    else:
        st.subheader("Available Tests")
        
        for test in all_tests:
            with st.expander(f"{test['test_data']['test_title']} - {test['role']} (Created: {test['created_at'].strftime('%Y-%m-%d %H:%M')})"):
                st.markdown(f"**Skills:** {test['skills']}")
                
                # Show test details
                st.markdown("### Test Structure")
                for section in test['test_data']['sections']:
                    st.markdown(f"#### {section['section_name']} ({section['total_marks']} marks)")
                    st.markdown(f"*{section['section_instructions']}*")
                    
                    # Show first few questions as sample
                    for i, question in enumerate(section['questions'][:2]):  # Show first 2 questions per section
                        st.markdown(f"{i+1}. {question['question_text']} ({question['marks']} marks)")
                    
                    if len(section['questions']) > 2:
                        st.markdown(f"... and {len(section['questions']) - 2} more questions")
                
                # Show responses statistics if any
                response_count = responses_collection.count_documents({"test_id": str(test['_id'])})
                st.markdown(f"**Responses Received:** {response_count}")
                
                if response_count > 0:
                    if st.button(f"View Responses for {test['test_data']['test_title']}", key=f"view_{test['_id']}"):
                        st.session_state['view_test_id'] = str(test['_id'])
                        st.rerun()
        
        # Detailed view for a specific test
        if 'view_test_id' in st.session_state:
            st.markdown("---")
            st.subheader("Test Responses")
            
            test_responses = list(responses_collection.find({"test_id": st.session_state['view_test_id']}))
            test_data = tests_collection.find_one({"_id": ObjectId(st.session_state['view_test_id'])})['test_data']
            
            st.markdown(f"### {test_data['test_title']} - Response Analysis")
            
            # Calculate statistics
            total_possible = sum(q['marks'] for section in test_data['sections'] for q in section['questions'])
            response_count = len(test_responses)
            
            if response_count > 0:
                avg_score = sum(resp.get('score', 0) for resp in test_responses) / response_count
                min_score = min(resp.get('score', 0) for resp in test_responses)
                max_score = max(resp.get('score', 0) for resp in test_responses)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Score", f"{avg_score:.1f}/{total_possible}")
                with col2:
                    st.metric("Highest Score", f"{max_score}/{total_possible}")
                with col3:
                    st.metric("Lowest Score", f"{min_score}/{total_possible}")
                
                # Display individual responses
                for response in test_responses:
                    with st.expander(f"{response['student_name']} ({response['student_email']}) - Score: {response.get('score', 'Not evaluated')}/{total_possible}"):
                        st.markdown(f"**Time Taken:** {(response['end_time'] - response['start_time']).total_seconds()/60:.1f} minutes")
                        
                        # Show responses for each question
                        for section in test_data['sections']:
                            st.markdown(f"#### {section['section_name']}")
                            for question in section['questions']:
                                question_id = question['question_id']
                                if question_id in response['responses']:
                                    resp_data = response['responses'][question_id]
                                    st.markdown(f"**Question:** {question['question_text']}")
                                    
                                    if question['question_type'].lower() == 'mcq':
                                        st.markdown(f"**Response:** {resp_data['response']}")
                                        st.markdown(f"**Correct Answer:** {question.get('correct_answer', 'N/A')}")
                                    
                                    elif question['question_type'].lower() == 'coding':
                                        st.markdown("**Code Submitted:**")
                                        st.code(resp_data['response'])
                                    
                                    st.markdown(f"**Marks Obtained:** {resp_data.get('score', 0)}/{question['marks']}")
                                    st.markdown("---")

# Evaluate Responses Page (Teacher only)
elif page == "Evaluate Responses" and st.session_state.test_data['user_type'] == 'teacher':
    st.header("📝 Evaluate Student Responses")
    
    # Get all tests with responses
    tests_with_responses = list(tests_collection.aggregate([
        {
            "$lookup": {
                "from": "responses",
                "localField": "_id",
                "foreignField": "test_id",
                "as": "responses"
            }
        },
        {
            "$match": {
                "responses": {"$ne": []}
            }
        }
    ]))
    
    if not tests_with_responses:
        st.warning("No tests with responses available for evaluation.")
    else:
        # Test selection
        test_options = {str(test['_id']): f"{test['test_data']['test_title']} ({test['role']}) - {len(test['responses'])} responses" 
                       for test in tests_with_responses}
        selected_test_id = st.selectbox("Select a test to evaluate", options=list(test_options.keys()), 
                                      format_func=lambda x: test_options[x])
        
        if selected_test_id:
            # Get unevaluated responses
            unevaluated_responses = list(responses_collection.find({
                "test_id": selected_test_id,
                "evaluated": False
            }))
            
            if not unevaluated_responses:
                st.success("All responses for this test have been evaluated!")
            else:
                response_to_evaluate = unevaluated_responses[0]
                test_data = tests_collection.find_one({"_id": ObjectId(selected_test_id)})['test_data']
                
                st.markdown(f"### Evaluating: {response_to_evaluate['student_name']} ({response_to_evaluate['student_email']})")
                
                with st.form("evaluation_form"):
                    total_marks = 0
                    obtained_marks = 0
                    
                    for section in test_data['sections']:
                        st.markdown(f"#### {section['section_name']}")
                        
                        for question in section['questions']:
                            question_id = question['question_id']
                            response = response_to_evaluate['responses'].get(question_id, {})
                            
                            st.markdown(f"**Question:** {question['question_text']} [{question['marks']} marks]")
                            
                            # Display student response
                            if question['question_type'].lower() == 'mcq':
                                st.markdown(f"**Student Answer:** {response.get('response', 'No answer')}")
                                st.markdown(f"**Correct Answer:** {question.get('correct_answer', 'N/A')}")
                            
                            elif question['question_type'].lower() == 'coding':
                                st.markdown("**Student Code:**")
                                st.code(response.get('response', '# No code submitted'))
                                
                                st.markdown("**Test Cases:**")
                                for i, test_case in enumerate(question.get('test_cases', []), 1):
                                    st.markdown(f"Case {i}: Input: `{test_case.get('input', '')}` → Expected Output: `{test_case.get('output', '')}`")
                            
                            # Evaluation input
                            marks = st.number_input(
                                f"Marks for this question (Max: {question['marks']})",
                                min_value=0,
                                max_value=question['marks'],
                                value=question['marks'] if response.get('evaluated', False) else 0,
                                key=f"marks_{question_id}"
                            )
                            
                            feedback = st.text_area(
                                "Feedback (optional)",
                                value=response.get('feedback', ''),
                                key=f"feedback_{question_id}"
                            )
                            
                            # Update response data
                            response_to_evaluate['responses'][question_id]['score'] = marks
                            response_to_evaluate['responses'][question_id]['feedback'] = feedback
                            response_to_evaluate['responses'][question_id]['evaluated'] = True
                            
                            total_marks += question['marks']
                            obtained_marks += marks
                            
                            st.markdown("---")
                    
                    # Submit evaluation
                    submitted = st.form_submit_button("Submit Evaluation")
                    if submitted:
                        # Update total score and mark as evaluated
                        response_to_evaluate['score'] = obtained_marks
                        response_to_evaluate['evaluated'] = True
                        
                        # Update in MongoDB
                        responses_collection.update_one(
                            {"_id": response_to_evaluate['_id']},
                            {"$set": response_to_evaluate}
                        )
                        
                        st.success("Evaluation submitted successfully!")
                        st.rerun()

# View Results Page (Student only)
elif page == "View Results" and st.session_state.test_data['user_type'] == 'student':
    st.header("📊 Your Test Results")
    
    # Get student's responses
    student_responses = list(responses_collection.find({
        "student_email": st.session_state.test_data['student_email']
    }))
    
    if not student_responses:
        st.warning("You haven't taken any tests yet.")
    else:
        for response in student_responses:
            test_data = tests_collection.find_one({"_id": ObjectId(response['test_id'])})['test_data']
            
            with st.expander(f"{test_data['test_title']} - Score: {response.get('score', 'Not evaluated')}/{sum(q['marks'] for section in test_data['sections'] for q in section['questions'])}"):
                st.markdown(f"**Taken on:** {response['start_time'].strftime('%Y-%m-%d %H:%M')}")
                
                if response.get('evaluated', False):
                    st.markdown("### Detailed Results")
                    
                    for section in test_data['sections']:
                        st.markdown(f"#### {section['section_name']}")
                        
                        for question in section['questions']:
                            question_id = question['question_id']
                            if question_id in response['responses']:
                                resp_data = response['responses'][question_id]
                                
                                st.markdown(f"**Question:** {question['question_text']}")
                                st.markdown(f"**Your Answer:**")
                                
                                if question['question_type'].lower() == 'mcq':
                                    st.markdown(resp_data.get('response', 'No answer'))
                                elif question['question_type'].lower() == 'coding':
                                    st.code(resp_data.get('response', '# No code submitted'))
                                else:
                                    st.markdown(resp_data.get('response', 'No answer'))
                                
                                st.markdown(f"**Marks Obtained:** {resp_data.get('score', 0)}/{question['marks']}")
                                
                                if resp_data.get('feedback'):
                                    st.markdown(f"**Feedback:** {resp_data['feedback']}")
                                
                                st.markdown("---")
                else:
                    st.info("Your test is still being evaluated. Please check back later.")