import base64
import json
import random
import cv2
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, current_app
from flask_mail import Message
from deepface import DeepFace

from app import mysql, mail
from app.utils.helpers import user_role_student, marks_calc
from app.utils.forms import TestForm
# IMPORTANT: Make sure your camera.py file is moved inside the app/utils/ folder!
import app.utils.camera as camera

# Create the Blueprint
student_bp = Blueprint('student', __name__)

@student_bp.route('/student_index')
@user_role_student
def student_index():
    return render_template('student_index.html')

@student_bp.route('/report_student')
@user_role_student
def report_student():
    return render_template('report_student.html')

@student_bp.route('/report_student_email', methods=['POST'])
@user_role_student
def report_student_email():
    careEmail = "braviadprogrammer@gmail.com"
    cname = session.get('name', 'N/A')
    cemail = session.get('email', 'N/A')
    ptype = request.form.get('prob_type', 'N/A')
    cquery = request.form.get('rquery', 'No query provided.')

    try:
        email_body = f"Problem Report from Student:\nName: {cname}\nEmail: {cemail}\nProblem Type: {ptype}\n\nQuery:\n{cquery}"
        msg = Message('PROBLEM REPORTED (Student) - MyProctor.ai', sender=current_app.config['MAIL_USERNAME'], recipients=[careEmail])
        msg.body = email_body
        mail.send(msg)
        flash('Your problem report has been submitted successfully.', 'success')
    except Exception as e:
        flash('An error occurred while submitting your report.', 'danger')
        
    return redirect(url_for('student.report_student'))

@student_bp.route('/<email>/student_test_history')
@user_role_student
def student_test_history(email):
     if email != session.get('email'):
         flash("Unauthorized access.", "danger")
         return redirect(url_for('student.student_index'))
     try:
         cur = mysql.connection.cursor()
         results = cur.execute("""
             SELECT a.test_id, b.subject, b.topic, b.test_type, b.end, b.show_ans
             FROM studentTestInfo a
             JOIN teachers b ON a.test_id = b.test_id
             WHERE a.email = %s AND a.uid = %s AND a.completed = 1
             ORDER BY b.end DESC
             """, (email, session['uid']))
         tests = cur.fetchall() if results > 0 else []
         cur.close()
         return render_template('student_test_history.html', tests=tests)
     except Exception as e:
         flash("Error retrieving your test history.", "danger")
         return render_template('student_test_history.html', tests=[])

# ==========================================
# VIEWING PUBLISHED RESULTS
# ==========================================
@student_bp.route('/<email>/tests-given', methods=['GET','POST'])
@user_role_student
def tests_given(email):
    if email != session.get('email'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('student.student_index'))

    if request.method == "GET":
        try:
            cur = mysql.connection.cursor()
            resultsTestids = cur.execute("""
                SELECT DISTINCT sti.test_id, t.subject, t.topic
                FROM studentTestInfo sti
                JOIN teachers t ON sti.test_id = t.test_id
                WHERE sti.email = %s AND sti.uid = %s AND sti.completed = 1 AND t.show_ans = 1
                ORDER BY t.end DESC
            """, (session['email'], session['uid']))
            test_list = cur.fetchall() if resultsTestids > 0 else []
            cur.close()
            return render_template('tests_given.html', cresults=test_list)
        except Exception:
            flash("Error retrieving your completed tests list.", "danger")
            return render_template('tests_given.html', cresults=[])

    if request.method == "POST":
        tidoption = request.form.get('choosetid')
        if not tidoption:
            flash("Please select a Test ID.", "warning")
            return redirect(url_for('student.tests_given', email=email))

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT t.test_type, t.show_ans, sti.completed
                FROM teachers t
                LEFT JOIN studentTestInfo sti ON t.test_id = sti.test_id AND sti.email = %s AND sti.uid = %s
                WHERE t.test_id = %s
            """, (email, session['uid'], tidoption))
            test_info = cur.fetchone()

            if not test_info or test_info['show_ans'] != 1 or test_info['completed'] != 1:
                 cur.close()
                 flash("Cannot view results for this test.", "warning")
                 return redirect(url_for('student.tests_given', email=email))

            test_type = test_info['test_type']
            studentResults = None 

            if test_type == "objective":
                score = marks_calc(email, tidoption)
                cur.execute("SELECT subject, topic FROM teachers WHERE test_id = %s", [tidoption])
                test_details = cur.fetchone()
                studentResults = [{'test_id': tidoption, 'subject': test_details.get('subject', 'N/A') if test_details else 'N/A', 'topic': test_details.get('topic', 'N/A') if test_details else 'N/A', 'marks': score}]
                template_name = 'obj_result_student.html'
            elif test_type == "subjective":
                cur.execute("""
                    SELECT SUM(lt.marks) AS marks, lt.test_id, t.subject, t.topic
                    FROM longtest lt
                    JOIN teachers t ON lt.test_id = t.test_id
                    WHERE lt.email = %s AND lt.test_id = %s
                    GROUP BY lt.test_id, t.subject, t.topic
                """, (email, tidoption))
                studentResults = cur.fetchall() 
                template_name = 'sub_result_student.html'
            elif test_type == "practical":
                cur.execute("""
                    SELECT SUM(pt.marks) AS marks, pt.test_id, t.subject, t.topic
                    FROM practicaltest pt
                    JOIN teachers t ON pt.test_id = t.test_id
                    WHERE pt.email = %s AND pt.test_id = %s
                    GROUP BY pt.test_id, t.subject, t.topic
                """, (email, tidoption))
                studentResults = cur.fetchall()
                template_name = 'prac_result_student.html'

            cur.close()
            return render_template(template_name, tests=studentResults)

        except Exception as e:
             flash("An error occurred while retrieving your results.", "danger")
             return redirect(url_for('student.tests_given', email=email))

@student_bp.route('/<email>/<testid>') 
@user_role_student
def check_result(email, testid):
    if email != session.get('email'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('student.student_index'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT t.show_ans, t.test_type, sti.completed
            FROM teachers t
            LEFT JOIN studentTestInfo sti ON t.test_id = sti.test_id AND sti.email = %s AND sti.uid = %s
            WHERE t.test_id = %s
        """, (email, session['uid'], testid))
        test_info = cur.fetchone()

        if not test_info or test_info['show_ans'] != 1 or test_info['completed'] != 1 or test_info['test_type'] != 'objective':
            cur.close()
            flash("Cannot view detailed results.", "warning")
            return redirect(url_for('student.tests_given', email=email))

        cur.execute("""
            SELECT q.q, q.a, q.b, q.c, q.d, q.marks, q.qid, q.ans AS correct, s.ans AS marked
            FROM questions q
            LEFT JOIN students s ON q.test_id = s.test_id AND q.qid = s.qid AND s.email = %s AND s.uid = %s
            WHERE q.test_id = %s
            ORDER BY LPAD(lower(q.qid), 10, '0') ASC
            """, (email, session['uid'], testid)) 

        detailed_results = cur.fetchall()
        cur.close()
        
        if detailed_results:
            return render_template('tests_result.html', results=detailed_results, test_id=testid)
        else:
            flash("No questions found for this test.", "warning")
            return redirect(url_for('student.tests_given', email=email))

    except Exception as e:
        flash("An error occurred retrieving detailed results.", "danger")
        return redirect(url_for('student.tests_given', email=email))

    # ==========================================
# EXAM ENTRY & PROCTORING FEEDS
# ==========================================
@student_bp.route("/give-test", methods=['GET', 'POST'])
@user_role_student
def give_test():
    form = TestForm(request.form) 

    if request.method == 'POST': 
        test_id = form.test_id.data
        password_candidate = form.password.data
        imgdata1_b64 = form.img_hidden_form.data 

        if not test_id or not password_candidate or not imgdata1_b64:
            flash("Test ID, Password, and Image Capture are required.", "danger")
            return render_template('give_test.html', form=form)

        try:
            cur1 = mysql.connection.cursor()
            results1 = cur1.execute('SELECT user_image FROM users WHERE email = %s AND uid = %s', (session['email'], session['uid']))
            if results1 > 0:
                cresults = cur1.fetchone()
                imgdata2_b64 = cresults['user_image']
                cur1.close()

                try:
                    nparr1 = np.frombuffer(base64.b64decode(imgdata1_b64), np.uint8)
                    nparr2 = np.frombuffer(base64.b64decode(imgdata2_b64), np.uint8)
                    image1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
                    image2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)

                    img_result = DeepFace.verify(image1, image2, enforce_detection=False, model_name='VGG-Face', distance_metric='cosine')

                    if not img_result.get("verified"):
                         flash('Image verification failed. Cannot start test.', 'danger')
                         return render_template('give_test.html', form=form)

                except Exception as face_error:
                    flash('An error occurred during image verification.', 'danger')
                    return render_template('give_test.html', form=form)
            else:
                cur1.close()
                flash("Error retrieving your registered image.", "danger")
                return render_template('give_test.html', form=form)

        except Exception as db_err:
             flash("Database error during identity verification.", "danger")
             return render_template('give_test.html', form=form)

        try:
            cur = mysql.connection.cursor()
            results = cur.execute('SELECT * FROM teachers WHERE test_id = %s', [test_id])
            if results > 0:
                data = cur.fetchone()
                if data['password'] == password_candidate:
                    now = datetime.now()
                    start_db, end_db = data['start'], data['end']
                    
                    if isinstance(start_db, datetime) and isinstance(end_db, datetime):
                        if not (start_db <= now <= end_db):
                            cur.close()
                            flash('Exam is not currently active.', 'warning')
                            return render_template('give_test.html', form=form)
                    else:
                        cur.close()
                        flash("Invalid test time configuration.", "danger")
                        return render_template('give_test.html', form=form)

                    cur.execute('SELECT time_to_sec(time_left) AS time_left, completed FROM studentTestInfo WHERE email = %s AND test_id = %s AND uid = %s', (session['email'], test_id, session['uid']))
                    student_info = cur.fetchone()

                    current_duration = data['duration'] 
                    is_resuming = False
                    marked_answers_json = "{}" 

                    if student_info:
                        if student_info['completed'] == 1:
                             cur.close()
                             flash('You have already completed this exam.', 'success')
                             return redirect(url_for('student.student_index'))
                        else:
                             is_resuming = True
                             time_left_db = student_info['time_left']
                             remaining_server_time = (end_db - now).total_seconds()
                             current_duration = min(time_left_db, data['duration'], remaining_server_time)
                             
                             if current_duration <= 0:
                                 cur.close()
                                 flash("Time for this exam has expired.", "warning")
                                 return redirect(url_for('student.student_index'))

                             if data['test_type'] == 'objective':
                                 cur.execute('SELECT qid, ans FROM students WHERE email = %s AND test_id = %s AND uid = %s', (session['email'], test_id, session['uid']))
                                 marked_results = cur.fetchall()
                                 marked_ans_dict = {row['qid']: row['ans'] for row in marked_results} if marked_results else {}
                                 marked_answers_json = json.dumps(marked_ans_dict)
                    else:
                        remaining_server_time = (end_db - now).total_seconds()
                        current_duration = min(data['duration'], remaining_server_time)
                        if current_duration <= 0:
                             cur.close()
                             flash("Not enough time remaining to start.", "warning")
                             return render_template('give_test.html', form=form)
                             
                        cur.execute('INSERT INTO studentTestInfo (email, test_id, time_left, completed, uid) VALUES (%s, %s, SEC_TO_TIME(%s), 0, %s)', (session['email'], test_id, current_duration, session['uid']))
                        mysql.connection.commit()

                    session['current_test_id'] = test_id
                    session['current_test_duration'] = int(current_duration)
                    session['current_test_calc'] = data['calc']
                    session['current_test_subject'] = data['subject']
                    session['current_test_topic'] = data['topic']
                    session['current_test_proctortype'] = data['proctoring_type']
                    session['current_test_type'] = data['test_type']
                    
                    if is_resuming and data['test_type'] == 'objective':
                         session['current_marked_ans'] = marked_answers_json
                    elif 'current_marked_ans' in session:
                         session.pop('current_marked_ans') 

                    cur.close()
                    return redirect(url_for('student.test', testid=test_id))
                else:
                    cur.close()
                    flash('Invalid test password.', 'danger')
                    return render_template('give_test.html', form=form)
            else:
                cur.close()
                flash('Invalid Test ID.', 'danger')
                return render_template('give_test.html', form=form)

        except Exception as e:
            flash("An error occurred while verifying test details.", "danger")
            return render_template('give_test.html', form=form)

    return render_template('give_test.html', form=form)

@student_bp.route('/video_feed', methods=['POST'])
@user_role_student
def video_feed():
    if 'current_test_id' not in session: return jsonify(error="No active test session"), 400
    try:
        imgData_b64 = request.form.get('data[imgData]')
        testid = request.form.get('data[testid]')
        voice_db_str = request.form.get('data[voice_db]', '0') 

        if testid != session.get('current_test_id'): return jsonify(error="Test ID mismatch"), 400
        if not imgData_b64: return jsonify(error="Missing image data"), 400

        try: proctorData = camera.get_frame(imgData_b64)
        except Exception: return jsonify(error="Error processing frame"), 500

        jpg_as_text = proctorData.get('jpg_as_text', imgData_b64) 
        mob_status = proctorData.get('mob_status', 0) 
        person_status = proctorData.get('person_status', 0) 
        user_move1 = proctorData.get('user_move1', 0) 
        user_move2 = proctorData.get('user_move2', 0) 
        eye_movements = proctorData.get('eye_movements', 0) 
        
        try: voice_db = float(voice_db_str)
        except ValueError: voice_db = 0.0 

        cur = mysql.connection.cursor()
        results = cur.execute("""
            INSERT INTO proctoring_log (email, name, test_id, voice_db, img_log, user_movements_updown, user_movements_lr, user_movements_eyes, phone_detection, person_status, uid, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,(session['email'], session['name'], testid, voice_db, jpg_as_text, user_move1, user_move2, eye_movements, mob_status, person_status, session['uid']))
        mysql.connection.commit()
        cur.close()

        if results > 0: return jsonify(status="recorded image of video") 
        else: return jsonify(error="error saving video log"), 500

    except Exception: return jsonify(error="Internal server error"), 500

@student_bp.route('/window_event', methods=['POST'])
@user_role_student
def window_event():
    if 'current_test_id' not in session: return jsonify(error="No active test session"), 400
    try:
        testid = request.form.get('testid')
        if testid != session.get('current_test_id'): return jsonify(error="Test ID mismatch"), 400

        cur = mysql.connection.cursor()
        results = cur.execute("INSERT INTO window_estimation_log (email, test_id, name, window_event, uid, timestamp) VALUES (%s, %s, %s, %s, %s, NOW())", (session['email'], testid, session['name'], 1, session['uid']))
        mysql.connection.commit()
        cur.close()

        if results > 0: return jsonify(status="recorded window event")
        else: return jsonify(error="error saving window event"), 500
    except Exception: return jsonify(error="Internal server error"), 500

    # ==========================================
# THE EXAM ENGINE
# ==========================================
@student_bp.route('/give-test/<testid>', methods=['GET','POST'])
@user_role_student
def test(testid):
    if 'current_test_id' not in session or session['current_test_id'] != testid:
         flash("Invalid test session. Please start again.", "warning")
         return redirect(url_for('student.give_test'))

    test_type = session.get('current_test_type')
    test_duration = session.get('current_test_duration')
    calc_enabled = session.get('current_test_calc')
    subject = session.get('current_test_subject')
    topic = session.get('current_test_topic')
    proctortype = session.get('current_test_proctortype')
    marked_ans_json = session.get('current_marked_ans', "{}") 

    if not test_type or test_duration is None:
         flash("Test session data missing.", "danger")
         return redirect(url_for('student.give_test'))

    if test_type == "objective":
        if request.method == 'GET':
            data = {'duration': test_duration, 'subject': subject, 'topic': topic, 'calc': calc_enabled, 'tid': testid, 'proctortype': proctortype}
            return render_template('testquiz.html', **data, answers=marked_ans_json)

        else: 
            flag = request.form.get('flag')
            if not flag: return jsonify(error="Missing flag parameter"), 400

            try:
                cur = mysql.connection.cursor()
                if flag == 'get': 
                    num = request.form.get('no')
                    results = cur.execute('SELECT test_id, qid, q, a, b, c, d, marks FROM questions WHERE test_id = %s AND qid = %s', (testid, num))
                    if results > 0:
                        data = cur.fetchone()
                        cur.close()
                        return jsonify(data) 
                    else:
                        cur.close()
                        return jsonify(error="Question not found"), 404

                elif flag == 'mark': 
                    qid = request.form.get('qid')
                    ans = str(request.form.get('ans', '')).upper() 
                    sql = "INSERT INTO students (email, test_id, qid, ans, uid) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ans = VALUES(ans)"
                    cur.execute(sql, (session['email'], testid, qid, ans, session['uid']))
                    mysql.connection.commit()
                    cur.close()
                    return jsonify(status='marked') 

                elif flag == 'time': 
                    time_left_str = request.form.get('time')
                    try:
                        time_left = max(0, int(float(time_left_str)))
                        cur.execute('UPDATE studentTestInfo SET time_left=SEC_TO_TIME(%s) WHERE test_id = %s AND email = %s AND uid = %s AND completed=0', (time_left, testid, session['email'], session['uid']))
                        mysql.connection.commit()
                        cur.close()
                        return jsonify({'time': 'fired'})
                    except ValueError:
                        cur.close()
                        return jsonify(error="Invalid time format"), 400

                elif flag == 'submit': 
                    cur.execute('UPDATE studentTestInfo SET completed=1, time_left=SEC_TO_TIME(0) WHERE test_id = %s AND email = %s AND uid = %s', (testid, session['email'], session['uid']))
                    mysql.connection.commit()
                    cur.close()
                    
                    # Clear test session variables safely
                    for key in ['current_test_id', 'current_test_duration', 'current_test_calc', 'current_test_subject', 'current_test_topic', 'current_test_proctortype', 'current_test_type', 'current_marked_ans']:
                        session.pop(key, None)
                        
                    flash("Exam submitted successfully!", 'success')
                    return jsonify({'sql': 'fired', 'redirect': url_for('student.student_index')}) 

            except Exception:
                mysql.connection.rollback()
                return jsonify(error="Internal error occurred."), 500

    elif test_type == "subjective":
        if request.method == 'GET':
            try:
                cur = mysql.connection.cursor()
                cur.execute('SELECT test_id, qid, q, marks FROM longqa WHERE test_id = %s ORDER BY qid ASC', [testid])
                callresults1 = cur.fetchall()
                cur.close()
                if not callresults1:
                     flash("No questions found.", "danger")
                     return redirect(url_for('student.give_test'))
                return render_template("testsubjective.html", callresults=callresults1, subject=subject, duration=test_duration, test_id=testid, topic=topic, proctortypes=proctortype)
            except Exception:
                 flash("Error loading questions.", "danger")
                 return redirect(url_for('student.give_test'))

        elif request.method == 'POST': 
            try:
                cur = mysql.connection.cursor()
                cur.execute('SELECT COUNT(qid) as q_count FROM longqa WHERE test_id = %s', [testid])
                q_data = cur.fetchone()
                num_questions = q_data['q_count'] if q_data else 0

                for i in range(1, num_questions + 1):
                    answerByStudent = request.form.get(str(i))
                    if answerByStudent is not None: 
                        sql = "INSERT INTO longtest (email, test_id, qid, ans, uid) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ans = VALUES(ans)"
                        cur.execute(sql, (session['email'], testid, i, answerByStudent, session['uid']))

                cur.execute('UPDATE studentTestInfo SET completed = 1, time_left=SEC_TO_TIME(0) WHERE test_id = %s AND email = %s AND uid = %s', (testid, session['email'], session['uid']))
                mysql.connection.commit()
                cur.close()
                
                for key in ['current_test_id', 'current_test_duration']: session.pop(key, None)
                flash('Exam Submitted Successfully!', 'success')
                return redirect(url_for('student.student_index'))
            except Exception:
                 mysql.connection.rollback()
                 flash('An error occurred during submission.', 'danger')
                 return redirect(url_for('student.test', testid=testid)) 

    elif test_type == "practical":
        if request.method == 'GET':
            try:
                cur = mysql.connection.cursor()
                cur.execute('SELECT test_id, qid, q, marks, compiler FROM practicalqa WHERE test_id = %s ORDER BY qid ASC', [testid])
                callresults1 = cur.fetchall() 
                cur.close()
                if not callresults1:
                     flash("No question found.", "danger")
                     return redirect(url_for('student.give_test'))
                return render_template("testpractical.html", callresults=callresults1, subject=subject, duration=test_duration, test_id=testid, topic=topic, proctortypep=proctortype) 
            except Exception:
                 flash("Error loading question.", "danger")
                 return redirect(url_for('student.give_test'))

        elif request.method == 'POST':
             try:
                 codeByStudent = request.form.get("codeByStudent")
                 inputByStudent = request.form.get("inputByStudent", "") 
                 executedByStudent = request.form.get("executedByStudent", "") 

                 cur = mysql.connection.cursor()
                 sql = "INSERT INTO practicaltest (email, test_id, qid, code, input, executed, uid) VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE code = VALUES(code), input = VALUES(input), executed = VALUES(executed)"
                 cur.execute(sql, (session['email'], testid, 1, codeByStudent, inputByStudent, executedByStudent, session['uid']))
                 cur.execute('UPDATE studentTestInfo SET completed = 1, time_left=SEC_TO_TIME(0) WHERE test_id = %s AND email = %s AND uid = %s', (testid, session['email'], session['uid']))
                 mysql.connection.commit()
                 cur.close()

                 for key in ['current_test_id', 'current_test_duration']: session.pop(key, None)
                 flash('Exam Submitted Successfully!', 'success')
                 return redirect(url_for('student.student_index'))
             except Exception:
                 mysql.connection.rollback()
                 flash('An error occurred during submission.', 'danger')
                 return redirect(url_for('student.test', testid=testid)) 

@student_bp.route('/randomize', methods=['POST'])
@user_role_student 
def random_gen():
    testid = request.form.get('id')
    if not testid or testid != session.get('current_test_id'): return jsonify(error="Unauthorized"), 403
    try:
        cur = mysql.connection.cursor()
        results = cur.execute('SELECT qid FROM questions WHERE test_id = %s ORDER BY qid ASC', [testid])
        if results > 0:
            qids_list = [str(q['qid']) for q in cur.fetchall()] 
            random.shuffle(qids_list)
            cur.close()
            return jsonify(qids_list) 
        else:
            cur.close()
            return jsonify(error="No questions found"), 404
    except Exception: return jsonify(error="Error generating order"), 500

@student_bp.route('/activities-detection')
@user_role_student
def background_activities_detection():
    # Make sure you have a file named 'activities_detection.html' in your templates folder!
    return render_template('activities_detection.html')

@student_bp.route('/real-time-monitoring')
@user_role_student
def real_time_monitoring():
    # Make sure you have a file named 'real_time_monitoring.html' in your templates folder!
    return render_template('real_time_monitoring.html')

@student_bp.route('/change-password-page')
@user_role_student
def change_password_page():
    # This route displays the visual form, which will then POST to auth.changePassword
    return render_template('changepassword_student.html')