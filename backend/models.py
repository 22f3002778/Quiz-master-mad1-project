from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User_Info(db.Model):
    __tablename__ = "user_info"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.Integer, default=1)  # 0 = admin, 1 = user
    full_name = db.Column(db.String, nullable=False)
    qualifications = db.Column(db.String, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    scores = db.relationship("Score", backref="user_info", cascade="all,delete", lazy=True)

class Subject(db.Model):
    __tablename__ = "subject"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    chapters = db.relationship("Chapter", backref="subject", lazy=True,cascade="all, delete-orphan")

class Chapter(db.Model):
    __tablename__ = "chapter"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id",ondelete="CASCADE"), nullable=False)
    quizzes = db.relationship("Quiz", backref="chapter", lazy=True)

class Quiz(db.Model):
    __tablename__ = "quiz"
    id = db.Column(db.Integer, primary_key=True)
    date_of_quiz = db.Column(db.Date, nullable=False)
    time_duration = db.Column(db.String, nullable=False)  # "HH:MM"
    remarks = db.Column(db.String(500))
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapter.id"), nullable=False)
    questions = db.relationship("Question", backref="quiz", lazy=True)
    scores = db.relationship("Score", backref="quiz_scores", lazy=True, overlaps="score_entries,quiz")

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    question_statement = db.Column(db.String, nullable=False)
    option1 = db.Column(db.String, nullable=False)
    option2 = db.Column(db.String, nullable=False)
    option3 = db.Column(db.String, nullable=False)
    option4 = db.Column(db.String, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 1-4
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id",ondelete="CASCADE"), nullable=False)

class Score(db.Model):
    __tablename__ = "score"
    id = db.Column(db.Integer, primary_key=True)
    total_scored = db.Column(db.Float)
    time_stamp_of_attempt = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user_info.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    quiz = db.relationship("Quiz", backref="score_entries", overlaps="quiz_scores,scores", viewonly=True)  # Made read-only