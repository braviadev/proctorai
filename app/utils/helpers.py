from app import mysql
import math, random
from functools import wraps
from flask import session, flash, redirect, url_for, render_template

def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(5):
        OTP += digits[math.floor(random.random() * 10)]
    return OTP

def user_role_professor(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session.get('user_role') == "teacher":
            return f(*args, **kwargs)
        elif 'logged_in' in session:
            flash('You dont have privilege to access this page!', 'danger')
            return render_template("404.html")
        else:
            flash('Unauthorized, Please login!', 'danger')
            # Notice we use 'auth.login' because login is now inside the auth blueprint
            return redirect(url_for('auth.login')) 
    return wrap

def user_role_student(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session.get('user_role') == "student":
            return f(*args, **kwargs)
        elif 'logged_in' in session:
            flash('You dont have privilege to access this page!', 'danger')
            return render_template("404.html")
        else:
            flash('Unauthorized, Please login!', 'danger')
            return redirect(url_for('auth.login'))
    return wrap

def examcreditscheck():
    if 'email' not in session or 'uid' not in session:
        return False
    cur = mysql.connection.cursor()
    results = cur.execute('SELECT examcredits from users where examcredits >= 1 and email = %s and uid = %s', (session['email'], session['uid']))
    cur.close()
    return results > 0

def examtypecheck(tidoption):
    if 'email' not in session or 'uid' not in session:
        return {} 
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT test_type from teachers where test_id = %s and email = %s and uid = %s', (tidoption, session['email'], session['uid']))
        callresults = cur.fetchone()
        cur.close()
        return callresults if callresults else {}
    except Exception as e:
        return {}

def displaywinstudentslogs(testid, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * from window_estimation_log where test_id = %s and email = %s and window_event = 1 ORDER BY timestamp DESC', (testid, email))
        callresults = cur.fetchall()
        cur.close()
        return callresults
    except Exception as e:
        return []

def countwinstudentslogs(testid, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT COUNT(*) as wincount from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
        callresults = cur.fetchone()
        cur.close()
        return callresults['wincount'] if callresults else 0
    except Exception as e:
        return 0

def countMobStudentslogs(testid, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT COUNT(*) as mobcount from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
        callresults = cur.fetchone()
        cur.close()
        return callresults['mobcount'] if callresults else 0
    except Exception as e:
        return 0

def countMTOPstudentslogs(testid, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
        callresults = cur.fetchone()
        cur.close()
        return callresults['percount'] if callresults else 0
    except Exception as e:
        return 0

def countTotalstudentslogs(testid, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT COUNT(*) as total from proctoring_log where test_id = %s and email = %s', (testid, email))
        callresults = cur.fetchone()
        cur.close()
        return callresults['total'] if callresults else 0
    except Exception as e:
        return 0

def neg_marks(email, testid, negm):
    sum_score = 0.0
    try:
        cur = mysql.connection.cursor()
        results = cur.execute("""
            SELECT q.marks, q.ans AS correct, s.ans AS marked
            FROM questions q
            JOIN students s ON q.test_id = s.test_id AND q.qid = s.qid
            WHERE q.test_id = %s AND s.email = %s
            ORDER BY q.qid ASC
        """, (testid, email))

        if results > 0:
            data = cur.fetchall()
            for row in data:
                marked_ans = str(row['marked']).upper() if row['marked'] else '0'
                correct_ans = str(row['correct']).upper()
                marks = int(row['marks'])

                if marked_ans != '0': # Only score answered questions
                    if marked_ans == correct_ans:
                        sum_score += marks
                    else:
                        sum_score -= (negm / 100.0) * marks
        cur.close()
    except Exception as e:
        return 0.0
    return sum_score

def marks_calc(email, testid):
    try:
        cur = mysql.connection.cursor()
        results = cur.execute("SELECT neg_marks FROM teachers WHERE test_id=%s", [testid])
        if results > 0:
            data = cur.fetchone()
            negm = data['neg_marks']
            cur.close() 
            return neg_marks(email, testid, negm)
        else:
            cur.close() 
            return 0.0 
    except Exception as e:
        return 0.0