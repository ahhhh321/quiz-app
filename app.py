import streamlit as st
from openai import OpenAI
import os
from datetime import datetime
import json
import pandas as pd
import glob
import matplotlib.pyplot as plt

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="Cybersecurity Quiz", layout="wide")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# LOAD TOPICS FROM FILE
# -------------------------------
def load_topics():
    try:
        with open("trainingcontent.txt") as f:
            return f.read()
    except:
        return "Cybersecurity Basics"

# -------------------------------
# GENERATE QUIZ
# -------------------------------
def generate_quiz(categories: str):
    messages = [
        {"role": "system", "content": "You are an expert cybersecurity instructor. Return ONLY valid JSON."},
        {"role": "user", "content": f"""
        Create EXACTLY 10 MCQs.

        FORMAT:
        {{
            "quiz":[
                {{
                    "question":"...",
                    "options":["A. ...","B. ...","C. ...","D. ..."],
                    "correct":"A",
                    "explanation":"...",
                    "category":"..."
                }}
            ]
        }}

        Topics:
        {categories}
        """}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=2000
    )

    return response.choices[0].message.content.strip()

# -------------------------------
# PARSE QUIZ
# -------------------------------
def parse_quiz(text):
    try:
        data = json.loads(text)
        return data["quiz"]
    except:
        return None

# -------------------------------
# SAVE QUIZ
# -------------------------------
def save_quiz(text):
    with open("quiz.json", "w") as f:
        json.dump({"quiz_text": text}, f)

# -------------------------------
# LOAD QUIZ
# -------------------------------
def load_quiz():
    try:
        with open("quiz.json") as f:
            return json.load(f)["quiz_text"]
    except:
        return None

# -------------------------------
# SAVE RESULTS
# -------------------------------
def save_results(name, score, accuracy, details):
    file = f"results_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(file, "w") as f:
        json.dump({
            "name": name,
            "score": score,
            "accuracy": accuracy,
            "details": details
        }, f, indent=4)
    return file

# -------------------------------
# LOAD ALL RESULTS
# -------------------------------
def load_results():
    data = []
    for file in glob.glob("results_*.json"):
        with open(file) as f:
            data.append(json.load(f))
    return data

# -------------------------------
# UI
# -------------------------------
st.title("🔐 Cybersecurity Quiz System")

mode = st.sidebar.selectbox("Mode", ["Teacher", "Student"])

# ===============================
# TEACHER MODE
# ===============================
if mode == "Teacher":
    st.header("👨‍🏫 Teacher Dashboard")

    topics = st.text_area("Topics", load_topics())

    if st.button("Generate Quiz"):
        with st.spinner("Generating..."):
            quiz_text = generate_quiz(topics)

            parsed = parse_quiz(quiz_text)

            if not parsed:
                st.error("❌ Invalid AI response. Try again.")
            else:
                save_quiz(quiz_text)
                st.success("✅ Quiz Generated")

                for q in parsed[:3]:
                    st.write("**", q["question"], "**")
                    st.write(q["options"])

    st.subheader("📊 Student Results")

    results = load_results()

    if results:
        df = pd.DataFrame([
            {
                "Name": r["name"],
                "Score": r["score"],
                "Accuracy": r["accuracy"]
            }
            for r in results
        ])

        st.dataframe(df)

        # Chart
        fig, ax = plt.subplots()
        ax.hist(df["Score"])
        st.pyplot(fig)

    else:
        st.info("No results yet")

# ===============================
# STUDENT MODE
# ===============================
if mode == "Student":
    st.header("🧑‍🎓 Take Quiz")

    name = st.text_input("Your Name")

    quiz_text = load_quiz()

    if not quiz_text:
        st.warning("No quiz available")
    else:
        parsed = parse_quiz(quiz_text)

        if not parsed:
            st.error("Quiz corrupted")
        else:
            answers = []

            for i, q in enumerate(parsed):
                st.subheader(f"Q{i+1}: {q['question']}")
                ans = st.radio("Select:", q["options"], key=i)
                answers.append(ans)

            if st.button("Submit"):
                score = 0
                details = []
                category_perf = {}

                for i, q in enumerate(parsed):
                    selected = answers[i][0]

                    correct = q["correct"]

                    is_correct = selected == correct

                    if is_correct:
                        score += 1

                    cat = q.get("category", "General")

                    if cat not in category_perf:
                        category_perf[cat] = {"correct": 0, "total": 0}

                    category_perf[cat]["total"] += 1
                    if is_correct:
                        category_perf[cat]["correct"] += 1

                    details.append({
                        "question": q["question"],
                        "your_answer": answers[i],
                        "correct": correct,
                        "explanation": q["explanation"]
                    })

                accuracy = round((score / len(parsed)) * 100, 2)

                st.success(f"Score: {score}/{len(parsed)}")
                st.info(f"Accuracy: {accuracy}%")

                # Show detailed feedback
                st.subheader("📘 Review")
                for d in details:
                    st.write("**Q:**", d["question"])
                    st.write("Your:", d["your_answer"])
                    st.write("Correct:", d["correct"])
                    st.write("Explain:", d["explanation"])
                    st.write("---")

                # Weak Areas
                st.subheader("📉 Performance by Category")
                for cat, val in category_perf.items():
                    acc = (val["correct"] / val["total"]) * 100
                    st.write(f"{cat}: {acc:.1f}%")

                file = save_results(name, score, accuracy, details)
                st.success(f"Saved: {file}")