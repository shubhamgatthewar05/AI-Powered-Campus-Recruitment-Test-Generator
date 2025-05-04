# 🏛️ AI-Powered Campus Recruitment Test Generator

This is an AI-powered web application that enables recruiters and educational institutions to **generate**, **manage**, and **evaluate** technical recruitment tests dynamically using **Google's Gemini LLM**, all through a user-friendly Streamlit interface.

## 🚀 Demo

🔗 [Live Demo Link]((https://qifeyp4vtq7.streamlit.app/))  
📝 **NOTE**: You can explore the demo, but API usage is limited due to restricted token access.

---

## 📌 Key Features

- ✨ **LLM-Based Test Generation**: Automatically generates technical tests tailored to job descriptions and required skills using Gemini (Gemini 1.5 Flash).
- 🧠 **AI Evaluation Engine**: Uses LLM to evaluate student responses, including code, MCQs, and subjective answers.
- 🧑‍💻 **Role-Based Access**: Separate dashboards for students and recruiters (teachers).
- 📊 **Test Analytics**: Visualizes performance using Matplotlib and Seaborn with section-wise and question-wise insights.
- 📂 **MongoDB Integration**: Stores users, test data, and responses securely.
- 📃 **PDF & CSV Reports**: Generates downloadable reports and certificates.
- 📈 **Real-Time Dashboards**: For test generation, response tracking, and feedback.

---

## 🛠️ Tech Stack

- **Frontend & Backend**: [Streamlit](https://streamlit.io/)
- **AI/LLM**: [Google Gemini API (gemini-1.5-flash)](https://makersuite.google.com/)
- **Database**: [MongoDB](https://www.mongodb.com/)
- **Styling**: Custom CSS
- **Visualization**: Matplotlib, Seaborn
- **Others**: dotenv, Python I/O, PDF/PNG export, base64

---



## ⚙️ Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
