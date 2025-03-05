from flask import Flask, render_template, request, redirect, url_for, g, session
from backend.models import db, User_Info, Subject, Chapter, Quiz, Question, Score
from datetime import datetime, date
import plotly.graph_objects as go
import os

# Initialization the app
app = Flask(__name__, static_folder='static')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///QuizApp.sqlite3"
app.debug = True
app.secret_key = 'your_secret_key_here'

# Initialize the database with the app
db.init_app(app)

# Set up the database (create tables and admin account)
def setup_db():
    with app.app_context():
        db.create_all()
        admin = User_Info.query.filter_by(email="admin@quizmaster.com").first()
        if not admin:
            admin = User_Info(
                email="admin@quizmaster.com",
                password="admin123",
                role=0,  # Ensure admin role is 0
                full_name="Quiz Master",
                qualifications="Admin",
                dob=date(2000, 1, 1)
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin account created with role 0!")
        print("Quiz app is working")

# Home route (render index.html)
@app.route("/")
def home():
    return render_template("index.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def signin():
    msg = request.args.get("msg", "")  # Get message from URL if present
    if request.method == "POST":
        uname = request.form.get("user_name")
        pwd = request.form.get("password")
        usr = User_Info.query.filter_by(email=uname, password=pwd).first()
        print(f"Login attempt: {uname}, {pwd}, User found: {usr}, Role: {usr.role if usr else None}")
        if not usr:
            return render_template("login.html", msg="Invalid credentials.")
        session['name'] = uname  # Store user's email in session
        print(f"Redirecting {uname} with role {usr.role} to dashboard")
        if usr.role == 0:
            return redirect(url_for("admin_dashboard", name=uname))
        elif usr.role == 1:
            return redirect(url_for("user_dashboard", name=uname))
    return render_template("login.html", msg=msg)

# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        uname = request.form.get("user_name")
        pwd = request.form.get("password")
        full_name = request.form.get("full_name")
        qualifications = request.form.get("qualifications")
        dob_str = request.form.get("dob")
        print(f"Signup: {uname}, {pwd}, {full_name}, {qualifications}, {dob_str}")
        if not all([uname, pwd, full_name, qualifications, dob_str]):
            return render_template("signup.html", msg="All fields are required!")
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template("signup.html", msg="Invalid Date Format (YYYY-MM-DD)!")
        usr = User_Info.query.filter_by(email=uname).first()
        if usr:
            return render_template("signup.html", msg="Email already registered!")
        new_usr = User_Info(email=uname, password=pwd, full_name=full_name, qualifications=qualifications, dob=dob, role=1)  # Default role 1 for users
        db.session.add(new_usr)
        db.session.commit()
        print(f"User {uname} registered successfully with role 1")
        session['name'] = uname  # Store user's email in session
        return redirect(url_for("signin", msg="Registered Successfully!"))  # Redirect to login
    return render_template("signup.html", msg="")

# Admin dashboard route
@app.route("/admin/<name>")
def admin_dashboard(name):
    subjects = Subject.query.all()
    subject_attempts = {}
    for subject in subjects:
        total_attempts = sum(len(chapter.quizzes) for chapter in subject.chapters if chapter.quizzes)
        subject_attempts[subject.name] = total_attempts or 0
    user_activity = {
        "Active Users": User_Info.query.filter(User_Info.scores.any()).count(),
        "Inactive Users": User_Info.query.filter(~User_Info.scores.any()).count()
    }
    print(f"Admin Dashboard for {name}, Subjects: {subjects}, Subject Attempts: {subject_attempts}, User Activity: {user_activity}")

    # Generate Plotly charts as HTML divs
    subject_attempts_chart = generate_subject_attempts_chart(subject_attempts)
    user_activity_chart = generate_user_activity_chart(user_activity)

    return render_template("admin_dashboard.html", name=name, subjects=subjects, 
                          subject_attempts_chart=subject_attempts_chart, user_activity_chart=user_activity_chart)

# User dashboard route
@app.route("/user/<name>")
def user_dashboard(name):
    subjects = Subject.query.all()
    user = User_Info.query.filter_by(email=name).first()
    scores = Score.query.filter_by(user_id=user.id).all()
    user_subject_scores = {}
    for score in scores:
        if score.quiz and score.quiz.chapter and score.quiz.chapter.subject:
            user_subject_scores[score.quiz.chapter.subject.name] = score.total_scored or 0.0
    user_quiz_attempts = {
        "Completed": len(scores),
        "Pending": max(0, len([q for s in subjects for c in s.chapters for q in c.quizzes]) - len(scores))
    }
    print(f"User Dashboard for {name}, Subject Scores: {user_subject_scores}, Quiz Attempts: {user_quiz_attempts}")

    # Generate Plotly charts as HTML divs
    user_subject_scores_chart = generate_user_subject_scores_chart(user_subject_scores)
    user_quiz_attempts_chart = generate_user_quiz_attempts_chart(user_quiz_attempts)

    return render_template("user_dashboard.html", name=name, subjects=subjects, 
                          user_subject_scores_chart=user_subject_scores_chart, user_quiz_attempts_chart=user_quiz_attempts_chart)

# Summary route
@app.route("/summary/<name>")
def summary(name):
    user = User_Info.query.filter_by(email=name).first()
    scores = Score.query.filter_by(user_id=user.id).all()
    user_subject_scores = {}
    for score in scores:
        if score.quiz and score.quiz.chapter and score.quiz.chapter.subject:
            user_subject_scores[score.quiz.chapter.subject.name] = score.total_scored or 0.0
    user_quiz_attempts = {
        "Completed": len(scores),
        "Pending": max(0, len([q for s in Subject.query.all() for c in s.chapters for q in c.quizzes]) - len(scores))
    }
    print(f"Summary for {name}, Subject Scores: {user_subject_scores}, Quiz Attempts: {user_quiz_attempts}")

    # Generate Plotly charts as HTML divs
    user_subject_scores_chart = generate_user_subject_scores_chart(user_subject_scores)
    user_quiz_attempts_chart = generate_user_quiz_attempts_chart(user_quiz_attempts)

    return render_template("summary.html", name=name, 
                          user_subject_scores_chart=user_subject_scores_chart, user_quiz_attempts_chart=user_quiz_attempts_chart)

# View quiz route
@app.route("/view_quiz/<int:quiz_id>/<name>")
def view_quiz(quiz_id, name):
    quiz = Quiz.query.get_or_404(quiz_id)
    print(f"Viewing quiz {quiz_id} for user {name}")
    return render_template("view_quiz.html", quiz=quiz, name=name)

# Attempt quiz route
@app.route("/quiz_attempt/<quiz_id>/<name>", methods=["GET", "POST"])
def attempt_quiz(quiz_id, name):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    if request.method == "POST":
        score = 0
        for question in questions:
            user_answer = request.form.get(f"question_{question.id}")
            if user_answer and int(user_answer) == question.correct_option:
                score += 1
        new_score = Score(
            total_scored=score, time_stamp_of_attempt=datetime.now(),
            user_id=User_Info.query.filter_by(email=name).first().id, quiz_id=quiz_id
        )
        db.session.add(new_score)
        db.session.commit()
        print(f"Quiz {quiz_id} attempted by {name}, Score: {score}")
        return redirect(url_for("quiz_scores", name=name))
    return render_template("attempt_quiz.html", name=name, quiz=quiz, questions=questions)

# Quiz scores route
@app.route("/quiz_scores/<name>")
def quiz_scores(name):
    user = User_Info.query.filter_by(email=name).first()
    scores = Score.query.filter_by(user_id=user.id).all()
    print(f"Quiz scores for {name}: {scores}")
    return render_template("quiz_scores.html", name=name, scores=scores)

# Search route
@app.route("/search/<name>", methods=["GET", "POST"])
def search(name):
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        subjects = Subject.query.filter(Subject.name.ilike(f"%{search_txt}%")).all()
        chapters = Chapter.query.filter(Chapter.name.ilike(f"%{search_txt}%")).all()
        quizzes = Quiz.query.filter(Quiz.remarks.ilike(f"%{search_txt}%")).all()
        users = User_Info.query.filter(User_Info.email.ilike(f"%{search_txt}%")).all()
        # Provide default chart data for search results
        subject_attempts = {subject.name: len(subject.chapters[0].quizzes) if subject.chapters else 0 for subject in subjects if subjects} or {"No Data": 0}
        user_activity = {"Active Users": 70, "Inactive Users": 30}  # Default data
        print(f"Search results for {name}: Subjects={len(subjects)}, Chapters={len(chapters)}, Quizzes={len(quizzes)}, Users={len(users)}")
        return render_template("admin_dashboard.html", name=name, subjects=subjects, chapters=chapters, quizzes=quizzes, users=users,
                              subject_attempts_chart=generate_subject_attempts_chart(subject_attempts), user_activity_chart=generate_user_activity_chart(user_activity))
    return redirect(url_for("admin_dashboard", name=name))

# Admin subject management routes
@app.route("/subject/<name>", methods=["GET", "POST"])
def add_subject(name):
    if request.method == "POST":
        sub_name = request.form.get("name")
        description = request.form.get("description")
        new_subject = Subject(name=sub_name, description=description)
        db.session.add(new_subject)
        db.session.commit()
        print(f"Added subject {sub_name} for {name}")
        return redirect(url_for("admin_dashboard", name=name))
    return render_template("add_subject.html", name=name)

@app.route("/edit_subject/<id>/<name>", methods=["GET", "POST"])
def edit_subject(id, name):
    subject = Subject.query.get_or_404(id)
    if request.method == "POST":
        subject.name = request.form.get("name")
        subject.description = request.form.get("description")
        db.session.commit()
        print(f"Edited subject {id} for {name}")
        return redirect(url_for("admin_dashboard", name=name))
    return render_template("edit_subject.html", subject=subject, name=name)

@app.route("/delete_subject/<id>/<name>", methods=["POST"])
def delete_subject(id, name):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    print(f"Deleted subject {id} for {name}")
    return redirect(url_for("admin_dashboard", name=name))

# Admin chapter management routes
@app.route("/chapter/<subject_id>/<name>", methods=["GET", "POST"])
def add_chapter(subject_id, name):
    if request.method == "POST":
        chapter_name = request.form.get("name")
        description = request.form.get("description")
        new_chapter = Chapter(name=chapter_name, description=description, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        print(f"Added chapter {chapter_name} for {name}")
        return redirect(url_for("admin_dashboard", name=name))
    return render_template("add_chapter.html", subject_id=subject_id, name=name)

@app.route("/edit_chapter/<id>/<name>", methods=["GET", "POST"])
def edit_chapter(id, name):
    chapter = Chapter.query.get_or_404(id)
    if request.method == "POST":
        chapter.name = request.form.get("name")
        chapter.description = request.form.get("description")
        db.session.commit()
        print(f"Edited chapter {id} for {name}")
        return redirect(url_for("admin_dashboard", name=name))
    return render_template("edit_chapter.html", chapter=chapter, name=name)

@app.route("/delete_chapter/<id>/<name>", methods=["POST"])
def delete_chapter(id, name):
    chapter = Chapter.query.get_or_404(id)
    db.session.delete(chapter)
    db.session.commit()
    print(f"Deleted chapter {id} for {name}")
    return redirect(url_for("admin_dashboard", name=name))

# Quiz management routes
@app.route("/quiz/<name>")
def quiz_dashboard(name):
    quizzes = Quiz.query.all()
    print(f"Quiz dashboard for {name}, Quizzes: {quizzes}")
    return render_template("quiz_dashboard.html", name=name, quizzes=quizzes)

@app.route("/add_quiz/<name>", methods=["GET", "POST"])
def add_quiz(name):
    if request.method == "POST":
        date_of_quiz = request.form.get("date_of_quiz")
        time_duration = request.form.get("time_duration")
        remarks = request.form.get("remarks")
        chapter_id = request.form.get("chapter_id")
        try:
            quiz_date = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
        except ValueError:
            return render_template("add_quiz.html", msg="Invalid Date Format (YYYY-MM-DD)!", name=name, chapters=Chapter.query.all())
        new_quiz = Quiz(date_of_quiz=quiz_date, time_duration=time_duration, remarks=remarks, chapter_id=chapter_id)
        db.session.add(new_quiz)
        db.session.commit()
        print(f"Added quiz for {name}")
        return redirect(url_for("quiz_dashboard", name=name))
    chapters = Chapter.query.all()
    return render_template("add_quiz.html", name=name, chapters=chapters)

@app.route("/edit_quiz/<quiz_id>/<name>", methods=["GET", "POST"])
def edit_quiz(quiz_id, name):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == "POST":
        date_of_quiz = request.form.get("date_of_quiz")
        try:
            quiz.date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
        except ValueError:
            return render_template("edit_quiz.html", msg="Invalid Date Format (YYYY-MM-DD)!", name=name, quiz=quiz)
        quiz.time_duration = request.form.get("time_duration")
        quiz.remarks = request.form.get("remarks")
        db.session.commit()
        print(f"Edited quiz {quiz_id} for {name}")
        return redirect(url_for("quiz_dashboard", name=name))
    return render_template("edit_quiz.html", name=name, quiz=quiz)

@app.route("/delete_quiz/<int:quiz_id>/<name>", methods=["POST"])
def delete_quiz(quiz_id, name):
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    print(f"Deleted quiz {quiz_id} for {name}")
    return redirect(url_for("quiz_dashboard", name=name))

# Question management routes
@app.route("/quiz/<int:quiz_id>/questions", methods=["GET", "POST"])
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == "POST":
        question_statement = request.form.get("question_statement")
        option1 = request.form.get("option1")
        option2 = request.form.get("option2")
        option3 = request.form.get("option3")
        option4 = request.form.get("option4")
        correct_option = int(request.form.get("correct_option"))
        new_question = Question(
            question_statement=question_statement, option1=option1, option2=option2,
            option3=option3, option4=option4, correct_option=correct_option, quiz_id=quiz_id
        )
        db.session.add(new_question)
        db.session.commit()
        print(f"Added question to quiz {quiz_id}")
        return redirect(url_for("quiz_dashboard", name=quiz.chapter.subject.name))
    return render_template("add_question.html", quiz=quiz)

@app.route("/edit_question/<int:id>", methods=["GET", "POST"])
def edit_question(id):
    question = Question.query.get_or_404(id)
    if request.method == "POST":
        question.question_statement = request.form.get("question_statement")
        question.option1 = request.form.get("option1")
        question.option2 = request.form.get("option2")
        question.option3 = request.form.get("option3")
        question.option4 = request.form.get("option4")
        question.correct_option = int(request.form.get("correct_option"))
        db.session.commit()
        print(f"Edited question {id}")
        return redirect(url_for("quiz_dashboard", name=question.quiz.chapter.subject.name))
    return render_template("edit_question.html", question=question)

@app.route("/delete_question/<int:id>", methods=["POST"])
def delete_question(id):
    question = Question.query.get_or_404(id)
    subject_name = question.quiz.chapter.subject.name if question.quiz and question.quiz.chapter and question.quiz.chapter.subject else "admin@quizmaster.com"
    db.session.delete(question)
    db.session.commit()
    print(f"Deleted question {id}")
    return redirect(url_for("quiz_dashboard", name=question.quiz.chapter.subject.name))

# Static file serving route
@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory('static', path)

# Session management
@app.before_request
def before_request():
    if 'name' in session:
        user = User_Info.query.filter_by(email=session['name']).first()
        if user:
            g.role = user.role  # Store role in Flask's global object for templates
            g.name = user.email
        else:
            session.pop('name', None)
            g.role = None
            g.name = None
    else:
        g.role = None
        g.name = None

@app.route("/logout")
def logout():
    session.pop('name', None)
    return redirect(url_for('home'))  # Redirect to home (index.html) after logout

# Chart generation functions using Plotly
def generate_subject_attempts_chart(subject_attempts):
    fig = go.Figure(data=[go.Bar(x=list(subject_attempts.keys()), y=list(subject_attempts.values()))])
    fig.update_layout(
        title='No of Quiz in subject',
        xaxis_title='Subjects',
        yaxis_title='Number of Quiz',
        xaxis={'tickangle': 45}
    )
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    return chart_html

def generate_user_activity_chart(user_activity):
    fig = go.Figure(data=[go.Pie(labels=list(user_activity.keys()), values=list(user_activity.values()))])
    fig.update_layout(title='User Activity')
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    return chart_html

def generate_user_subject_scores_chart(user_subject_scores):
    fig = go.Figure(data=[go.Bar(x=list(user_subject_scores.keys()), y=list(user_subject_scores.values()))])
    fig.update_layout(
        title='Your Subject-wise Scores',
        xaxis_title='Subjects',
        yaxis_title='Scores',
        yaxis={'range': [0, 100]},  # Assuming scores are out of 100
        xaxis={'tickangle': 45}
    )
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    return chart_html

def generate_user_quiz_attempts_chart(user_quiz_attempts):
    fig = go.Figure(data=[go.Pie(labels=list(user_quiz_attempts.keys()), values=list(user_quiz_attempts.values()))])
    fig.update_layout(title='Your Quiz Attempts')
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    return chart_html

setup_db()

if __name__ == "__main__":
    app.run()