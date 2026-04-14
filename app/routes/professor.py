import os
import stripe
import re
from datetime import datetime
import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, current_app
from flask_mail import Message
from coolname import generate_slug
from app import mysql, mail
from app.utils.forms import UploadForm, QAUploadForm, PracUploadForm
from app.utils.helpers import (
    user_role_professor, examcreditscheck, examtypecheck, 
    displaywinstudentslogs, countwinstudentslogs, countMobStudentslogs, 
    countMTOPstudentslogs, countTotalstudentslogs, marks_calc
)

# Configure Stripe using the safe .env variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Create the Blueprint
professor_bp = Blueprint('professor', __name__)

@professor_bp.route('/professor_index')
@user_role_professor
def professor_index():
    return render_template('professor_index.html')

@professor_bp.route('/report_professor')
@user_role_professor
def report_professor():
    return render_template('report_professor.html')

@professor_bp.route('/report_professor_email', methods=['POST'])
@user_role_professor
def report_professor_email():
    careEmail = "braviadprogrammer@gmail.com" 
    cname = session.get('name', 'N/A')
    cemail = session.get('email', 'N/A')
    ptype = request.form.get('prob_type', 'N/A')
    cquery = request.form.get('rquery', 'No query provided.')

    try:
        email_body = f"""
        Problem Report from Professor:
        Name: {cname}
        Email: {cemail}
        Problem Type: {ptype}

        Query:
        {cquery}
        """
        msg = Message('PROBLEM REPORTED (Professor) - MyProctor.ai',
                      sender=current_app.config['MAIL_USERNAME'],
                      recipients=[careEmail])
        msg.body = email_body
        mail.send(msg)
        flash('Your problem report has been submitted successfully.', 'success')
    except Exception as e:
        flash('An error occurred while submitting your report. Please try again later.', 'danger')

    return redirect(url_for('professor.report_professor'))

@professor_bp.route('/create-test', methods=['GET', 'POST']) 
@user_role_professor
def create_test_objective(): 
    form = UploadForm()
    if form.validate_on_submit():
        test_id = generate_slug(2)
        if not examcreditscheck():
            flash("Insufficient exam credits.", "warning")
            return redirect(url_for('professor.professor_index'))

        try:
            filestream = form.doc.data
            filestream.seek(0)
            df = pd.read_csv(filestream)
            
            # Data validation and cleaning
            df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
            df.dropna(subset=['qid', 'q', 'ans', 'marks'], inplace=True)
            df.fillna('', inplace=True)

            start_date_time = datetime.strptime(f"{form.start_date.data} {form.start_time.data}", "%Y-%m-%d %H:%M:%S")
            end_date_time = datetime.strptime(f"{form.end_date.data} {form.end_time.data}", "%Y-%m-%d %H:%M:%S")
            duration_seconds = int(form.duration.data) * 60

            cur = mysql.connection.cursor()
            for index, row in df.iterrows():
                cur.execute("""
                    INSERT INTO questions(test_id, qid, q, a, b, c, d, ans, marks, uid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (test_id, row['qid'], row['q'], row['a'], row['b'], row['c'], row['d'], str(row['ans']).upper(), int(row['marks']), session['uid']))

            cur.execute("""
                INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, neg_marks, calc, proctoring_type, uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,(session['email'], test_id, "objective", start_date_time, end_date_time, duration_seconds, 0, form.password.data, form.subject.data, form.topic.data, form.neg_mark.data, 1 if form.calc.data else 0, form.proctor_type.data, session['uid']))

            cur.execute('UPDATE users SET examcredits = examcredits - 1 WHERE email = %s AND uid = %s', (session['email'], session['uid']))
            mysql.connection.commit()
            cur.close()

            flash(f'Objective Exam "{form.subject.data}" created successfully! Exam ID: {test_id}', 'success')
            return redirect(url_for('professor.professor_index'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while creating the test: {e}", 'danger')

    elif request.method == 'POST':
         flash('There were errors in the form. Please check the fields below.', 'danger')

    return render_template('create_test.html', form=form)

@professor_bp.route('/create_test_lqa', methods=['GET', 'POST'])
@user_role_professor
def create_test_lqa():
    form = QAUploadForm()
    if form.validate_on_submit():
        test_id = generate_slug(2)
        if not examcreditscheck():
            flash("Insufficient exam credits.", "warning")
            return redirect(url_for('professor.professor_index'))

        try:
            filestream = form.doc.data
            filestream.seek(0)
            df = pd.read_csv(filestream)
            df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
            df.dropna(subset=['marks'], inplace=True)

            start_date_time = datetime.strptime(f"{form.start_date.data} {form.start_time.data}", "%Y-%m-%d %H:%M:%S")
            end_date_time = datetime.strptime(f"{form.end_date.data} {form.end_time.data}", "%Y-%m-%d %H:%M:%S")
            duration_seconds = int(form.duration.data) * 60

            cur = mysql.connection.cursor()
            for index, row in df.iterrows():
                cur.execute('INSERT INTO longqa(test_id, qid, q, marks, uid) values(%s, %s, %s, %s, %s)', (test_id, row['qid'], row['q'], int(row['marks']), session['uid']))

            cur.execute("""
                INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, neg_marks, calc, proctoring_type, uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,(session['email'], test_id, "subjective", start_date_time, end_date_time, duration_seconds, 0, form.password.data, form.subject.data, form.topic.data, 0, 0, form.proctor_type.data, session['uid']))

            cur.execute('UPDATE users SET examcredits = examcredits - 1 WHERE email = %s AND uid = %s', (session['email'], session['uid']))
            mysql.connection.commit()
            cur.close()

            flash(f'Subjective Exam "{form.subject.data}" created successfully! Exam ID: {test_id}', 'success')
            return redirect(url_for('professor.professor_index'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while creating the test: {e}", 'danger')

    return render_template('create_test_lqa.html', form=form)

# ==========================================
# STRIPE PAYMENT ROUTES
# ==========================================
@professor_bp.route("/config")
@user_role_professor
def get_publishable_key():
    stripe_config = {"publicKey": os.getenv('STRIPE_PUBLISHABLE_KEY')}
    return jsonify(stripe_config)

@professor_bp.route('/create-checkout-session', methods=['POST'])
@user_role_professor
def create_checkout_session():
    plan_name = 'Basic Exam Plan of 10 units'
    unit_amount_cents = 499 * 100 
    currency = 'inr'
    product_image = 'https://i.imgur.com/LsvO3kL_d.webp?maxwidth=760&fidelity=grand' 

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'unit_amount': unit_amount_cents,
                    'product_data': {'name': plan_name, 'images': [product_image]},
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'user_email': session.get('email'), 'user_uid': session.get('uid')},
            success_url=url_for('professor.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('professor.cancelled', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error={'message': "Failed to create payment session."}), 500

@professor_bp.route("/success")
@user_role_professor
def success():
    checkout_session_id = request.args.get('session_id')
    if not checkout_session_id:
        flash("Payment verification failed.", 'danger')
        return redirect(url_for('professor.payment'))

    try:
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        if checkout_session.payment_status == "paid":
            cur = mysql.connection.cursor()
            updated = cur.execute('UPDATE users SET examcredits = examcredits + 10 WHERE email = %s AND uid = %s', (session['email'], session['uid']))
            mysql.connection.commit()
            cur.close()
            
            if updated > 0:
                flash("Payment successful! 10 exam credits have been added.", 'success')
            else:
                flash("Payment successful, but failed to update credits.", 'warning')
            return render_template("success.html")
        else:
            flash(f"Payment status is {checkout_session.payment_status}.", 'warning')
            return redirect(url_for('professor.payment'))
    except Exception as e:
        flash("An error occurred verifying payment.", 'danger')
        return redirect(url_for('professor.payment'))

@professor_bp.route("/cancelled")
@user_role_professor
def cancelled():
    flash("Your payment was cancelled.", 'info')
    return render_template("cancelled.html")

@professor_bp.route("/payment")
@user_role_professor
def payment():
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT examcredits FROM users WHERE email = %s AND uid = %s', (session['email'], session['uid']))
        callresults = cur.fetchone()
        cur.close()
        credits = callresults['examcredits'] if callresults else 0
        return render_template("payment.html", key=os.getenv('STRIPE_PUBLISHABLE_KEY'), callresults={'examcredits': credits})
    except Exception as e:
        flash("Error retrieving your current exam credits.", 'danger')
        return render_template("payment.html", key=os.getenv('STRIPE_PUBLISHABLE_KEY'), callresults={'examcredits': 'Error'})

# ==========================================
# TEST MANAGEMENT (VIEWING & DELETING)
# ==========================================
@professor_bp.route('/viewquestions', methods=['GET'])
@user_role_professor
def viewquestions():
    try:
        cur = mysql.connection.cursor()
        results = cur.execute('SELECT test_id, subject, topic FROM teachers WHERE email = %s AND uid = %s ORDER BY start DESC', (session['email'], session['uid']))
        test_list = cur.fetchall() if results > 0 else []
        cur.close()
        return render_template("viewquestions.html", cresults=test_list)
    except Exception as e:
        flash("Error retrieving your test list.", "danger")
        return render_template("viewquestions.html", cresults=[])

@professor_bp.route('/displayquestions', methods=['POST'])
@user_role_professor
def displayquestions():
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.viewquestions'))

    et_result = examtypecheck(tidoption)
    test_type = et_result.get('test_type') if et_result else None

    if not test_type:
         flash(f"Test ID '{tidoption}' not found or you do not have permission.", "danger")
         return redirect(url_for('professor.viewquestions'))

    try:
        cur = mysql.connection.cursor()
        if test_type == "objective":
            cur.execute('SELECT * FROM questions WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "displayquestions.html"
        elif test_type == "subjective":
            cur.execute('SELECT * FROM longqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "displayquestionslong.html"
        elif test_type == "practical":
            cur.execute('SELECT * FROM practicalqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "displayquestionspractical.html"
            
        cur.close()
        return render_template(template_name, callresults=callresults, test_id=tidoption)
    except Exception as e:
        flash("An error occurred while retrieving questions.", "danger")
        return redirect(url_for('professor.viewquestions'))

@professor_bp.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
    try:
        cur = mysql.connection.cursor()
        results = cur.execute('SELECT test_id, subject, topic, start FROM teachers WHERE email = %s AND uid = %s', (session['email'], session['uid']))
        if results > 0:
            all_tests = cur.fetchall()
            now = datetime.now()
            eligible_tests = [t for t in all_tests if isinstance(t.get('start'), datetime) and t['start'] > now]
            cur.close()
            return render_template("deltidlist.html", cresults=eligible_tests)
        cur.close()
        return render_template("deltidlist.html", cresults=[])
    except Exception as e:
        flash("Error retrieving test list for deletion.", "danger")
        return render_template("deltidlist.html", cresults=[])

@professor_bp.route('/deldispques', methods=['POST']) 
@user_role_professor
def deldispques():
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.deltidlist'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT test_type, start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (tidoption, session['email'], session['uid']))
        test_info = cur.fetchone()

        if not test_info:
            flash(f"Test ID '{tidoption}' not found or access denied.", "danger")
            return redirect(url_for('professor.deltidlist'))

        start_time = test_info.get('start')
        if isinstance(start_time, datetime) and start_time <= datetime.now():
             flash(f"Cannot delete questions from Test ID '{tidoption}' because it has already started.", "warning")
             return redirect(url_for('professor.deltidlist'))

        test_type = test_info.get('test_type')
        
        if test_type == "objective":
            cur.execute('SELECT * FROM questions WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "deldispques.html"
        elif test_type == "subjective":
            cur.execute('SELECT * FROM longqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "deldispquesLQA.html"
        elif test_type == "practical":
             cur.execute('SELECT * FROM practicalqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
             callresults = cur.fetchall()
             template_name = "deldispquesPQA.html"

        cur.close()
        return render_template(template_name, callresults=callresults, tid=tidoption) 
    except Exception as e:
        flash("An error occurred while retrieving questions for deletion.", "danger")
        return redirect(url_for('professor.deltidlist'))

@professor_bp.route('/delete_questions/<testid>', methods=['POST'])
@user_role_professor
def delete_questions(testid):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT test_type, start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (testid, session['email'], session['uid']))
        test_info = cur.fetchone()

        if not test_info:
            return jsonify(error="Test not found or access denied."), 403

        start_time = test_info.get('start')
        if isinstance(start_time, datetime) and start_time <= datetime.now():
             return jsonify(error="Cannot delete questions, test has already started."), 400

        test_type = test_info.get('test_type')
        qids_to_delete_str = request.json.get('qids')

        if not qids_to_delete_str:
            return jsonify(error="No question IDs provided for deletion."), 400

        qids_to_delete = [qid.strip() for qid in qids_to_delete_str.split(',') if qid.strip()]
        
        table_name = None
        if test_type == "objective": table_name = "questions"
        elif test_type == "subjective": table_name = "longqa"
        elif test_type == "practical": table_name = "practicalqa"

        placeholders = ', '.join(['%s'] * len(qids_to_delete))
        sql = f"DELETE FROM {table_name} WHERE test_id = %s AND uid = %s AND qid IN ({placeholders})"
        params = [testid, session['uid']] + qids_to_delete

        cur.execute(sql, params)
        deleted_count = cur.rowcount
        mysql.connection.commit()
        cur.close()

        return jsonify(message=f'<span style=\'color:green;\'>{deleted_count} question(s) deleted successfully</span>', deleted_count=deleted_count), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify(error="An error occurred during question deletion."), 500

# ==========================================
# TEST MANAGEMENT (UPDATING QUESTIONS)
# ==========================================
@professor_bp.route('/updatetidlist', methods=['GET'])
@user_role_professor
def updatetidlist():
    try:
        cur = mysql.connection.cursor()
        results = cur.execute('SELECT test_id, subject, topic, start FROM teachers WHERE email = %s AND uid = %s', (session['email'], session['uid']))
        if results > 0:
            all_tests = cur.fetchall()
            now = datetime.now()
            # Only show tests that haven't started yet
            eligible_tests = [t for t in all_tests if isinstance(t.get('start'), datetime) and t['start'] > now]
            cur.close()
            return render_template("updatetidlist.html", cresults=eligible_tests)
        cur.close()
        return render_template("updatetidlist.html", cresults=[])
    except Exception as e:
        flash("Error retrieving test list for updating.", "danger")
        return render_template("updatetidlist.html", cresults=[])


@professor_bp.route('/updatedispques', methods=['POST'])
@user_role_professor
def updatedispques():
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.updatetidlist'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT test_type, start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (tidoption, session['email'], session['uid']))
        test_info = cur.fetchone()

        if not test_info:
            flash(f"Test ID '{tidoption}' not found or access denied.", "danger")
            return redirect(url_for('professor.updatetidlist'))

        start_time = test_info.get('start')
        if isinstance(start_time, datetime) and start_time <= datetime.now():
             flash("Cannot update questions because the test has already started.", "warning")
             return redirect(url_for('professor.updatetidlist'))

        test_type = test_info.get('test_type')
        
        if test_type == "objective":
            cur.execute('SELECT * FROM questions WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "updatedispques.html"
        elif test_type == "subjective":
            cur.execute('SELECT * FROM longqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "updatedispquesLQA.html"
        elif test_type == "practical":
            cur.execute('SELECT * FROM practicalqa WHERE test_id = %s AND uid = %s ORDER BY qid ASC', (tidoption, session['uid']))
            callresults = cur.fetchall()
            template_name = "updatedispquesPQA.html"

        cur.close()
        return render_template(template_name, callresults=callresults, test_id=tidoption)

    except Exception as e:
        flash("An error occurred while retrieving questions for update.", "danger")
        return redirect(url_for('professor.updatetidlist'))

@professor_bp.route('/update/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_quiz(testid, qid): # For Objective Questions
    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (testid, session['email'], session['uid']))
        test_info = cur_check.fetchone()
        cur_check.close()
        
        if not test_info:
            flash("Test not found or access denied.", "danger")
            return redirect(url_for('professor.updatetidlist'))
            
        start_time = test_info.get('start')
        if isinstance(start_time, datetime) and start_time <= datetime.now():
            flash("Cannot update questions, the test has already started.", "warning")
            return redirect(url_for('professor.updatetidlist'))
    except Exception as e:
        flash("An error occurred verifying test status.", "danger")
        return redirect(url_for('professor.updatetidlist'))

    if request.method == 'POST':
        ques = request.form.get('ques')
        ao = request.form.get('ao')
        bo = request.form.get('bo')
        co = request.form.get('co')
        do = request.form.get('do')
        anso = str(request.form.get('anso', '')).upper()
        markso_str = request.form.get('mko')

        if not ques or anso == '' or markso_str is None:
            flash("Question, Answer, and Marks are required fields.", "warning")
            return redirect(url_for('professor.updatetidlist'))

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE questions SET q = %s, a = %s, b = %s, c = %s, d = %s, ans = %s, marks = %s
                WHERE test_id = %s AND qid = %s AND uid = %s
                """, (ques, ao, bo, co, do, anso, int(markso_str), testid, qid, session['uid']))
            mysql.connection.commit()
            cur.close()
            flash('Question updated successfully.', 'success')
            return redirect(url_for('professor.updatetidlist'))
        except Exception as e:
            mysql.connection.rollback()
            flash('An error occurred while updating the question.', 'danger')
            return redirect(url_for('professor.updatetidlist'))

    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM questions WHERE test_id = %s AND qid = %s AND uid = %s', (testid, qid, session['uid']))
        uresults = cur.fetchall()
        cur.close()
        if uresults:
            return render_template("updateQuestions.html", uresults=uresults)
        else:
            flash("Question not found.", "danger")
            return redirect(url_for('professor.updatetidlist'))
    except Exception as e:
        flash("Error retrieving question details.", "danger")
        return redirect(url_for('professor.updatetidlist'))


@professor_bp.route('/updateLQA/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_lqa(testid, qid): # For Subjective Questions
    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (testid, session['email'], session['uid']))
        test_info = cur_check.fetchone()
        cur_check.close()
        if not test_info or (isinstance(test_info.get('start'), datetime) and test_info.get('start') <= datetime.now()):
            flash("Cannot update questions, the test has already started or access denied.", "warning")
            return redirect(url_for('professor.updatetidlist'))
    except Exception as e: return redirect(url_for('professor.updatetidlist'))

    if request.method == 'POST':
        ques = request.form.get('ques')
        markso_str = request.form.get('mko')

        if not ques or markso_str is None:
            flash("Question and Marks are required.", "warning")
            return redirect(url_for('professor.updatetidlist'))

        try:
            cur = mysql.connection.cursor()
            cur.execute('UPDATE longqa SET q = %s, marks = %s WHERE test_id = %s AND qid = %s AND uid = %s',
                        (ques, int(markso_str), testid, qid, session['uid']))
            mysql.connection.commit()
            cur.close()
            flash('Question updated successfully.', 'success')
            return redirect(url_for('professor.updatetidlist'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Database error updating question.', 'danger')
            return redirect(url_for('professor.updatetidlist'))

    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM longqa WHERE test_id = %s AND qid = %s AND uid = %s', (testid, qid, session['uid']))
        uresults = cur.fetchall()
        cur.close()
        if uresults: return render_template("updateQuestionsLQA.html", uresults=uresults)
        flash("Question not found.", "danger")
        return redirect(url_for('professor.updatetidlist'))
    except Exception as e: return redirect(url_for('professor.updatetidlist'))


@professor_bp.route('/updatePQA/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_PQA(testid, qid): # For Practical Questions
    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT start FROM teachers WHERE test_id = %s AND email = %s AND uid = %s", (testid, session['email'], session['uid']))
        test_info = cur_check.fetchone()
        cur_check.close()
        if not test_info or (isinstance(test_info.get('start'), datetime) and test_info.get('start') <= datetime.now()):
            flash("Cannot update questions, the test has already started or access denied.", "warning")
            return redirect(url_for('professor.updatetidlist'))
    except Exception as e: return redirect(url_for('professor.updatetidlist'))

    if request.method == 'POST':
        ques = request.form.get('ques')
        markso_str = request.form.get('mko')

        if not ques or markso_str is None:
            flash("Question and Marks are required.", "warning")
            return redirect(url_for('professor.updatetidlist'))

        try:
            cur = mysql.connection.cursor()
            cur.execute('UPDATE practicalqa SET q = %s, marks = %s WHERE test_id = %s AND qid = %s AND uid = %s',
                        (ques, int(markso_str), testid, qid, session['uid']))
            mysql.connection.commit()
            cur.close()
            flash('Question updated successfully.', 'success')
            return redirect(url_for('professor.updatetidlist'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Database error updating question.', 'danger')
            return redirect(url_for('professor.updatetidlist'))

    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM practicalqa WHERE test_id = %s AND qid = %s AND uid = %s', (testid, qid, session['uid']))
        uresults = cur.fetchall()
        cur.close()
        if uresults: return render_template("updateQuestionsPQA.html", uresults=uresults)
        flash("Question not found.", "danger")
        return redirect(url_for('professor.updatetidlist'))
    except Exception as e: return redirect(url_for('professor.updatetidlist'))

# ==========================================
# PROCTORING LOGS & MONITORING
# ==========================================
@professor_bp.route('/viewstudentslogs', methods=['GET'])
@user_role_professor
def viewstudentslogs():
    try:
        cur = mysql.connection.cursor()
        results = cur.execute("""
            SELECT test_id, subject, topic FROM teachers
            WHERE email = %s AND uid = %s AND proctoring_type = 0
            ORDER BY start DESC
        """, (session['email'], session['uid']))
        cresults = cur.fetchall() if results > 0 else []
        cur.close()
        return render_template("viewstudentslogs.html", cresults=cresults)
    except Exception as e:
        flash("Error retrieving test list for viewing logs.", "danger")
        return render_template("viewstudentslogs.html", cresults=[])

@professor_bp.route('/displaystudentsdetails', methods=['POST']) 
@user_role_professor
def displaystudentsdetails():
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.viewstudentslogs'))

    et_result = examtypecheck(tidoption) 
    if not et_result:
        flash(f"Test ID '{tidoption}' not found or access denied.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT DISTINCT pl.email, pl.test_id, u.name
            FROM proctoring_log pl
            JOIN users u ON pl.email = u.email AND u.user_type = 'student'
            WHERE pl.test_id = %s
            ORDER BY u.name
        """, [tidoption])
        callresults = cur.fetchall()
        cur.close()
        return render_template("displaystudentsdetails.html", callresults=callresults, test_id=tidoption)
    except Exception as e:
        flash("An error occurred retrieving student details.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

@professor_bp.route('/displaystudentslogs/<testid>/<email>', methods=['GET'])
@user_role_professor
def displaystudentslogs(testid, email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM proctoring_log WHERE test_id = %s AND email = %s ORDER BY timestamp DESC', (testid, email))
        callresults = cur.fetchall()
        cur.close()
        return render_template("displaystudentslogs.html", testid=testid, email=email, callresults=callresults)
    except Exception as e:
        flash("Error retrieving logs.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

@professor_bp.route('/mobdisplaystudentslogs/<testid>/<email>', methods=['GET'])
@user_role_professor
def mobdisplaystudentslogs(testid, email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM proctoring_log WHERE test_id = %s AND email = %s AND phone_detection = 1 ORDER BY timestamp DESC', (testid, email))
        callresults = cur.fetchall()
        cur.close()
        return render_template("mobdisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)
    except Exception:
        flash("Error retrieving mobile detection logs.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

@professor_bp.route('/persondisplaystudentslogs/<testid>/<email>', methods=['GET'])
@user_role_professor
def persondisplaystudentslogs(testid, email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM proctoring_log WHERE test_id = %s AND email = %s AND person_status = 1 ORDER BY timestamp DESC', (testid, email))
        callresults = cur.fetchall()
        cur.close()
        return render_template("persondisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)
    except Exception:
        flash("Error retrieving person status logs.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

@professor_bp.route('/audiodisplaystudentslogs/<testid>/<email>', methods=['GET'])
@user_role_professor
def audiodisplaystudentslogs(testid, email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM proctoring_log WHERE test_id = %s AND email = %s ORDER BY timestamp DESC', (testid, email)) 
        callresults = cur.fetchall()
        cur.close()
        return render_template("audiodisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)
    except Exception:
        flash("Error retrieving audio logs.", "danger")
        return redirect(url_for('professor.viewstudentslogs'))

@professor_bp.route('/wineventstudentslogs/<testid>/<email>', methods=['GET'])
@user_role_professor
def wineventstudentslogs(testid, email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    callresults = displaywinstudentslogs(testid, email) 
    return render_template("wineventstudentlog.html", testid=testid, email=email, callresults=callresults)

@professor_bp.route('/studentmonitoringstats/<testid>/<email>', methods=['GET'])
@user_role_professor
def studentmonitoringstats(testid,email):
    if not examtypecheck(testid): return redirect(url_for('professor.professor_index'))
    return render_template("stat_student_monitoring.html", testid=testid, email=email)

@professor_bp.route('/ajaxstudentmonitoringstats/<testid>/<email>', methods=['GET'])
@user_role_professor
def ajaxstudentmonitoringstats(testid,email):
    if not examtypecheck(testid): return jsonify(error="Access denied"), 403
    win_count = countwinstudentslogs(testid, email)
    mob_count = countMobStudentslogs(testid, email)
    per_count = countMTOPstudentslogs(testid, email)
    tot_count = countTotalstudentslogs(testid, email)
    return jsonify({"win": win_count, "mob": mob_count, "per": per_count, "tot": tot_count})

# ==========================================
# ENTERING MARKS (SUBJECTIVE/PRACTICAL)
# ==========================================
@professor_bp.route('/insertmarkstid', methods=['GET'])
@user_role_professor
def insertmarkstid():
    try:
        cur = mysql.connection.cursor()
        results = cur.execute("""
            SELECT test_id, subject, topic, end FROM teachers
            WHERE email = %s AND uid = %s AND show_ans = 0
            AND (test_type = 'subjective' OR test_type = 'practical')
            ORDER BY end DESC
        """, (session['email'], session['uid']))

        if results > 0:
            all_tests = cur.fetchall()
            now = datetime.now()
            eligible_tests = [t for t in all_tests if isinstance(t.get('end'), datetime) and t['end'] < now]
            cur.close()
            return render_template("insertmarkstid.html", cresults=eligible_tests)
        cur.close()
        return render_template("insertmarkstid.html", cresults=[])
    except Exception as e:
        flash("Error retrieving test list for marking.", "danger")
        return render_template("insertmarkstid.html", cresults=[])

@professor_bp.route('/insertmarksdetails', methods=['POST']) 
@user_role_professor
def insertmarksdetails():
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.insertmarkstid'))

    et_result = examtypecheck(tidoption)
    test_type = et_result.get('test_type') if et_result else None

    if not test_type or test_type not in ['subjective', 'practical']:
        flash("Test ID not found, is not subjective/practical, or access denied.", "danger")
        return redirect(url_for('professor.insertmarkstid'))

    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT end, show_ans FROM teachers WHERE test_id = %s", [tidoption])
        test_status = cur_check.fetchone()
        cur_check.close()
        if not test_status or test_status['show_ans'] == 1 or (isinstance(test_status.get('end'), datetime) and test_status['end'] >= datetime.now()):
             flash("Cannot enter marks. Test may not be finished or results already published.", "warning")
             return redirect(url_for('professor.insertmarkstid'))
    except Exception:
         flash("Error verifying test status.", "danger")
         return redirect(url_for('professor.insertmarkstid'))

    try:
        cur = mysql.connection.cursor()
        student_table = "longtest" if test_type == "subjective" else "practicaltest"
        template_name = "subdispstudentsdetails.html" if test_type == "subjective" else "pracdispstudentsdetails.html"

        cur.execute(f"""
            SELECT DISTINCT st.email, st.test_id, u.name
            FROM {student_table} st
            JOIN users u ON st.email = u.email AND u.user_type = 'student'
            JOIN studentTestInfo sti ON st.email = sti.email AND st.test_id = sti.test_id
            WHERE st.test_id = %s AND sti.completed = 1
            ORDER BY u.name
        """, [tidoption])
        callresults = cur.fetchall()
        cur.close()
        return render_template(template_name, callresults=callresults, test_id=tidoption)

    except Exception as e:
        flash("An error occurred retrieving the student list.", "danger")
        return redirect(url_for('professor.insertmarkstid'))
# ==========================================
# PUBLISHING & SHARING RESULTS
# ==========================================
@professor_bp.route("/publish-results-testid", methods=['GET']) 
@user_role_professor
def publish_results_testid_list(): 
    try:
        cur = mysql.connection.cursor()
        results = cur.execute("""
            SELECT test_id, subject, topic, end FROM teachers
            WHERE email = %s AND uid = %s AND show_ans = 0
            AND (test_type = 'subjective' OR test_type = 'practical')
            AND end < NOW()
            ORDER BY end DESC
        """, (session['email'], session['uid']))

        eligible_tests = cur.fetchall() if results > 0 else []
        cur.close()
        return render_template("publish_results_testid.html", cresults=eligible_tests)
    except Exception as e:
        flash("Error retrieving test list for publishing.", "danger")
        return render_template("publish_results_testid.html", cresults=[])

@professor_bp.route('/viewresults', methods=['POST']) 
@user_role_professor
def viewresults_before_publish(): 
    tidoption = request.form.get('choosetid')
    if not tidoption:
        flash("Please select a Test ID.", "warning")
        return redirect(url_for('professor.publish_results_testid_list'))

    et_result = examtypecheck(tidoption)
    test_type = et_result.get('test_type') if et_result else None

    if not test_type or test_type not in ['subjective', 'practical']:
        flash("Test ID not found, is not subjective/practical, or access denied.", "danger")
        return redirect(url_for('professor.publish_results_testid_list'))

    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT end, show_ans FROM teachers WHERE test_id = %s", [tidoption])
        test_status = cur_check.fetchone()
        cur_check.close()
        if not test_status or test_status['show_ans'] == 1 or (isinstance(test_status.get('end'), datetime) and test_status['end'] >= datetime.now()):
             flash("Cannot view/publish results. Test may not be finished or results already published.", "warning")
             return redirect(url_for('professor.publish_results_testid_list'))

        cur = mysql.connection.cursor()
        student_table = "longtest" if test_type == "subjective" else "practicaltest"

        cur.execute(f"""
            SELECT SUM(st.marks) AS marks, st.email, u.name
            FROM {student_table} st
            JOIN users u ON st.email = u.email AND u.user_type = 'student'
            WHERE st.test_id = %s
            GROUP BY st.email, u.name
            ORDER BY u.name
        """, [tidoption])
        callresults = cur.fetchall()
        cur.close()

        return render_template("publish_viewresults.html", callresults=callresults, tid=tidoption)
    except Exception as e:
        flash("An error occurred retrieving the results summary.", "danger")
        return redirect(url_for('professor.publish_results_testid_list'))

@professor_bp.route('/publish_results', methods=['POST']) 
@user_role_professor
def publish_results():
    tidoption = request.form.get('testidsp') 
    if not tidoption:
        flash("Test ID missing. Cannot publish.", "danger")
        return redirect(url_for('professor.publish_results_testid_list'))

    et_result = examtypecheck(tidoption)
    test_type = et_result.get('test_type') if et_result else None
    if not test_type or test_type not in ['subjective', 'practical']:
        flash("Test ID not found or invalid type for publishing.", "danger")
        return redirect(url_for('professor.publish_results_testid_list'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT end, show_ans FROM teachers WHERE test_id = %s", [tidoption])
        test_status = cur.fetchone()
        if not test_status or test_status['show_ans'] == 1 or (isinstance(test_status.get('end'), datetime) and test_status['end'] >= datetime.now()):
             cur.close()
             flash("Cannot publish results. Test may not be finished or results already published.", "warning")
             return redirect(url_for('professor.publish_results_testid_list'))

        updated = cur.execute('UPDATE teachers SET show_ans = 1 WHERE test_id = %s AND email = %s AND uid = %s', (tidoption, session['email'], session['uid']))
        mysql.connection.commit()
        cur.close()

        if updated > 0:
            flash(f"Results for Test ID {tidoption} published successfully!", 'success')
        else:
            flash("Failed to publish results. Database update error.", 'danger')

        return redirect(url_for('professor.professor_index')) 

    except Exception as e:
        mysql.connection.rollback()
        flash("An error occurred while publishing results.", 'danger')
        return redirect(url_for('professor.publish_results_testid_list'))

@professor_bp.route('/<email>/<testid>/share_details', methods=['GET']) 
@user_role_professor
def share_details_form(email, testid): 
    if email != session.get('email'):
        flash("Unauthorized access.", "danger")
        return redirect(url_for('professor.professor_index'))

    et_result = examtypecheck(testid)
    if not et_result:
        flash("Test not found or access denied.", "danger")
        return redirect(url_for('professor.professor_index'))

    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM teachers WHERE test_id = %s AND email = %s AND uid = %s', (testid, email, session['uid']))
        callresults = cur.fetchone() 
        cur.close()
        if callresults:
             if callresults.get('duration'):
                  callresults['duration_minutes'] = callresults['duration'] // 60
             return render_template("share_details.html", callresults=callresults) 
        else:
             flash("Could not retrieve test details for sharing.", "danger")
             return redirect(url_for('professor.professor_index'))
    except Exception as e:
         flash("Error retrieving test details.", "danger")
         return redirect(url_for('professor.professor_index'))

@professor_bp.route('/share_details_emails', methods=['POST']) 
@user_role_professor
def share_details_emails():
    try:
        tid = request.form.get('tid')
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        duration_minutes = request.form.get('duration') 
        start_str = request.form.get('start')
        end_str = request.form.get('end')
        password = request.form.get('password') 
        neg_marks = request.form.get('neg_marks')
        calc = request.form.get('calc') 
        emailssharelist_str = request.form.get('emailssharelist')

        if not tid or not emailssharelist_str:
            flash("Test ID and recipient email(s) are required.", "warning")
            return redirect(url_for('professor.professor_index')) 

        recipients = [email.strip() for email in re.split(r'[,\s\n]+', emailssharelist_str) if email.strip()]
        if not recipients:
             flash("No valid recipient email addresses provided.", "warning")
             return redirect(url_for('professor.professor_index'))

        email_body = f"""
        Hello,

        Please find the details for the upcoming exam:

        Exam ID: {tid}
        Subject: {subject}
        Topic: {topic}
        Duration: {duration_minutes} minutes
        Start Time: {start_str}
        End Time: {end_str}
        Password: {password}  (Please keep this secure)
        Negative Marks (%): {neg_marks}
        Calculator Allowed: {'Yes' if str(calc) == '1' else 'No'}

        Please be prepared for the exam during the scheduled window.

        Regards,
        {session.get('name', 'Your Professor')}
        (via MyProctor.ai)
        """

        msg = Message(f'Exam Details: {subject} ({tid}) - MyProctor.ai',
                      sender=current_app.config['MAIL_USERNAME'],
                      recipients=[current_app.config['MAIL_USERNAME']], 
                      bcc=recipients) 
        msg.body = email_body
        mail.send(msg)

        flash('Exam details emailed successfully to recipients!', 'success')
        return redirect(url_for('professor.professor_index'))

    except Exception as e:
        flash('An error occurred while sending the email details.', 'danger')
        return redirect(url_for('professor.professor_index'))

@professor_bp.route('/<email>/disptests')
@user_role_professor
def disptests(email):
     if email != session.get('email'):
         flash("Unauthorized access.", "danger")
         return redirect(url_for('professor.professor_index'))
     try:
         cur = mysql.connection.cursor()
         results = cur.execute("""
             SELECT test_id, subject, topic, test_type, start, end, show_ans
             FROM teachers
             WHERE email = %s AND uid = %s
             ORDER BY start DESC
             """, (email, session['uid']))
         tests = cur.fetchall() if results > 0 else []
         cur.close()
         return render_template('disptests.html', tests=tests)
     except Exception as e:
         flash("Error retrieving your test list.", "danger")
         return render_template('disptests.html', tests=[])

@professor_bp.route('/<email>/tests-created')
@user_role_professor
def tests_created(email):
     if email != session.get('email'):
         flash("Unauthorized access.", "danger")
         return redirect(url_for('professor.professor_index'))
     try:
         cur = mysql.connection.cursor()
         results = cur.execute("""
             SELECT test_id, subject, topic, test_type, end
             FROM teachers
             WHERE email = %s AND uid = %s AND show_ans = 1
             ORDER BY end DESC
             """, (email, session['uid']))
         tests = cur.fetchall() if results > 0 else []
         cur.close()
         return render_template('tests_created.html', tests=tests)
     except Exception as e:
         flash("Error retrieving published tests list.", "danger")
         return render_template('tests_created.html', tests=[])

@professor_bp.route('/<email>/tests-created/<testid>', methods = ['GET']) 
@user_role_professor
def student_results(email, testid):
    if email != session.get('email'):
        flash("Unauthorized access.", "danger")
        return redirect(url_for('professor.professor_index'))

    et_result = examtypecheck(testid) 
    test_type = et_result.get('test_type') if et_result else None
    if not test_type:
        flash("Test not found or access denied.", "danger")
        return redirect(url_for('professor.tests_created', email=email))

    try:
        cur_check = mysql.connection.cursor()
        cur_check.execute("SELECT show_ans FROM teachers WHERE test_id = %s", [testid])
        status = cur_check.fetchone()
        cur_check.close()
        if not status or status['show_ans'] != 1:
             flash("Results for this test are not published yet.", "warning")
             return redirect(url_for('professor.tests_created', email=email))
    except Exception as e:
        flash("Error verifying test status.", "danger")
        return redirect(url_for('professor.tests_created', email=email))

    final_results = []
    names = []
    scores = []
    template_name = None

    try:
        cur = mysql.connection.cursor()
        if test_type == "objective":
            cur.execute("""
                SELECT u.name, u.email, sti.test_id
                FROM studentTestInfo sti
                JOIN users u ON sti.email = u.email AND sti.uid = u.uid
                WHERE sti.test_id = %s AND sti.completed = 1 AND u.user_type = 'student'
                ORDER BY u.name
                """, (testid,))
            students = cur.fetchall()
            count = 1
            for user in students:
                score = marks_calc(user['email'], user['test_id']) 
                final_results.append({'srno': count, 'name': user['name'], 'email': user['email'], 'marks': score})
                names.append(user['name'])
                scores.append(score)
                count += 1
            template_name = 'student_results.html'

        elif test_type == "subjective":
            cur.execute("""
                SELECT u.name, u.email, lt.test_id, SUM(lt.marks) AS marks
                FROM longtest lt
                JOIN users u ON lt.email = u.email AND lt.uid = u.uid
                JOIN studentTestInfo sti ON lt.email = sti.email AND lt.test_id = sti.test_id
                WHERE lt.test_id = %s AND sti.completed = 1 AND u.user_type = 'student'
                GROUP BY u.name, u.email, lt.test_id
                ORDER BY u.name
                """, (testid,))
            final_results = cur.fetchall()
            count = 1
            for user in final_results: 
                 user['srno'] = count 
                 names.append(user['name'])
                 scores.append(user['marks'] if user['marks'] is not None else 0)
                 count += 1
            template_name = 'student_results_lqa.html'

        elif test_type == "practical":
             cur.execute("""
                SELECT u.name, u.email, pt.test_id, SUM(pt.marks) AS marks
                FROM practicaltest pt
                JOIN users u ON pt.email = u.email AND pt.uid = u.uid
                JOIN studentTestInfo sti ON pt.email = sti.email AND pt.test_id = sti.test_id
                WHERE pt.test_id = %s AND sti.completed = 1 AND u.user_type = 'student'
                GROUP BY u.name, u.email, pt.test_id
                ORDER BY u.name
                """, (testid,))
             final_results = cur.fetchall()
             count = 1
             for user in final_results:
                 user['srno'] = count
                 names.append(user['name'])
                 scores.append(user['marks'] if user['marks'] is not None else 0)
                 count += 1
             template_name = 'student_results_pqa.html'

        else:
             flash("Invalid test type for viewing results.", "danger")
             cur.close()
             return redirect(url_for('professor.tests_created', email=email))

        cur.close()
        return render_template(template_name, data=final_results, labels=names, values=scores, test_id=testid)

    except Exception as e:
        flash("An error occurred retrieving student results.", "danger")
        return redirect(url_for('professor.tests_created', email=email))

@professor_bp.route('/create-test-pqa')
@user_role_professor
def create_test_pqa():
    return render_template('create_prac_qa.html')

@professor_bp.route('/generate-test')
@user_role_professor
def generate_test():
    return render_template('generate_test.html')

@professor_bp.route('/live-monitoring-tid')
@user_role_professor
def livemonitoringtid():
    return render_template('livemonitoringtid.html')

@professor_bp.route('/activities-detection')
@user_role_professor
def background_activities_detection():
    return render_template('activities_detect.html')

@professor_bp.route('/real-time-monitoring')
@user_role_professor
def real_time_monitoring():
    return render_template('real_time_background_activities_detection.html')

@professor_bp.route('/change-password-page')
@user_role_professor
def change_password_page():
    return render_template('changepassword_professor.html')