from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from app import mysql, mail
import random  
from app.utils.helpers import generateOTP
import base64, cv2, numpy as np
from deepface import DeepFace

# Create the Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        # 1. Grab the raw password and strip hidden spaces
        raw_password = request.form.get('password')
        clean_password = raw_password.strip() if raw_password else ""
        
        user_type = request.form.get('user_type')
        imgdata = request.form.get('image_hidden')

        if not name or not email or not clean_password or not user_type or not imgdata:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        cur = mysql.connection.cursor()
        email_exists = cur.execute("SELECT uid FROM users WHERE email = %s", [email])
        cur.close()
        
        if email_exists > 0:
            flash('Email address already registered.', 'warning')
            return render_template('register.html')

        # Restored to the scrypt standard
        hashed_password = generate_password_hash(clean_password, method='scrypt')

        session['tempName'] = name
        session['tempEmail'] = email
        session['tempPassword'] = hashed_password 
        session['tempUT'] = user_type
        session['tempImage'] = imgdata

        # Generate a 5-digit OTP
        sesOTP = str(random.randint(10000, 99999))
        session['tempOTP'] = sesOTP

        try:
            msg1 = Message('MyProctor.ai - OTP Verification', sender=current_app.config['MAIL_USERNAME'], recipients=[email])
            msg1.body = f"Your OTP Verification code is {sesOTP}."
            mail.send(msg1)
            flash('OTP sent to your email. Please verify.', 'info')
        except Exception as e:
            flash('Error sending email. Please check your email configuration.', 'danger')
            print(f"Mail Error: {e}")
        
        return redirect(url_for('auth.verifyEmail'))

    return render_template('register.html')

@auth_bp.route('/verifyEmail', methods=['GET', 'POST'])
def verifyEmail():
    if request.method == 'POST':
        theOTP = request.form.get('eotp')
        if theOTP == session.get('tempOTP'):
            cur = mysql.connection.cursor()
            # Notice we are saving the hashed password, not plain text
            cur.execute('INSERT INTO users(name, email, password, user_type, user_image, user_login, examcredits) values(%s,%s,%s,%s,%s,%s,%s)',
                        (session['tempName'], session['tempEmail'], session['tempPassword'], session['tempUT'], session['tempImage'], 0, 0))
            mysql.connection.commit()
            cur.close()

            session.clear() # Clear temp data
            flash("Successfully registered! You can now log in.", 'success')
            return redirect(url_for('auth.login'))
        else:
            return render_template('verifyEmail.html', error="Incorrect OTP.")
            
    return render_template('verifyEmail.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_candidate = request.form.get('password')
        user_type = request.form.get('user_type')
        imgdata1_b64 = request.form.get('image_hidden')

        cur = mysql.connection.cursor()
        results1 = cur.execute('SELECT uid, name, email, password, user_type, user_image, user_login from users where email = %s and user_type = %s', (email, user_type))

        if results1 > 0:
            cresults = cur.fetchone()
            stored_password_hash = cresults['password']

            # Check if the user is already logged in
            if cresults['user_login'] == 1:
                cur.close()
                flash('Account logged in elsewhere.', 'warning')
                return render_template('login.html')

            # --- DEBUGGING X-RAY ---
            print("=== LOGIN DEBUG ===")
            print(f"1. Email trying to log in: '{email}'")
            print(f"2. Raw Password Typed: '{password_candidate}'")
            print(f"3. Database Hash: '{stored_password_hash}'")
            print("===================")

            # We add .strip() just in case the browser added a hidden space!
            clean_password = password_candidate.strip() if password_candidate else ""

            # Verify the hashed password securely (with a fallback for old plain-text test accounts)
            if check_password_hash(stored_password_hash, clean_password) or stored_password_hash == clean_password:
                imgdata2_b64 = cresults['user_image']
                
                try:
                    nparr1 = np.frombuffer(base64.b64decode(imgdata1_b64), np.uint8)
                    nparr2 = np.frombuffer(base64.b64decode(imgdata2_b64), np.uint8)
                    image1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
                    image2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)

                    img_result = DeepFace.verify(image1, image2, enforce_detection=False, model_name='VGG-Face', distance_metric='cosine')

                    if img_result.get("verified") == True:
                        cur.execute('UPDATE users SET user_login = 1 WHERE email = %s AND uid = %s', (email, cresults['uid']))
                        mysql.connection.commit()
                        cur.close()

                        session['logged_in'] = True
                        session['email'] = email
                        session['name'] = cresults['name']
                        session['user_role'] = user_type
                        session['uid'] = cresults['uid']

                        if user_type == "student":
                            return redirect(url_for('student.student_index')) 
                        else:
                            return redirect(url_for('professor.professor_index')) 
                    else:
                        flash('Image verification failed. Please ensure your face is clearly visible.', 'danger')
                except Exception as e:
                    flash('Error processing facial recognition.', 'danger')
            else:
                flash('Invalid password.', 'danger')
        else:
            flash('Invalid email or user type.', 'danger')
            
        cur.close()
        
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'logged_in' in session:
        cur = mysql.connection.cursor()
        cur.execute('UPDATE users SET user_login = 0 WHERE email = %s AND uid = %s', (session['email'], session['uid']))
        mysql.connection.commit()
        cur.close()
        session.clear()
        flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/lostpassword', methods=['GET', 'POST'])
def lostpassword():
    if request.method == 'POST':
        lpemail = request.form.get('lpemail')
        if not lpemail:
            flash('Please enter your email address.', 'warning')
            return render_template('lostpassword.html')

        cur = mysql.connection.cursor()
        results = cur.execute('SELECT uid from users where email = %s', [lpemail])
        cur.close()
        
        if results > 0:
            sesOTPfp = generateOTP()
            session['tempOTPfp'] = sesOTPfp
            session['seslpemail'] = lpemail 
            
            try:
                msg1 = Message('MyProctor.ai - Password Reset OTP', sender=current_app.config['MAIL_USERNAME'], recipients=[lpemail])
                msg1.body = f"Your OTP Verification code for resetting your password is {sesOTPfp}."
                mail.send(msg1)
                flash('An OTP has been sent to your email address.', 'info')
                return redirect(url_for('auth.verifyOTPfp'))
            except Exception as mail_error:
                flash('Failed to send OTP email. Please try again later.', 'danger')
                return render_template('lostpassword.html')
        else:
            flash("Account not found for this email address.", 'danger')
            return render_template('lostpassword.html')

    return render_template('lostpassword.html')

@auth_bp.route('/verifyOTPfp', methods=['GET', 'POST'])
def verifyOTPfp():
    if 'tempOTPfp' not in session or 'seslpemail' not in session:
        flash("Session expired. Please start again.", 'warning')
        return redirect(url_for('auth.lostpassword'))

    if request.method == 'POST':
        fpOTP = request.form.get('fpotp')
        if fpOTP == session.get('tempOTPfp'):
            session.pop('tempOTPfp', None)
            session['otp_verified_for_reset'] = True
            return redirect(url_for('auth.lpnewpwd'))
        else:
            flash("Incorrect OTP entered.", 'danger')
            
    return render_template('verifyOTPfp.html')

@auth_bp.route('/lpnewpwd', methods=['GET', 'POST'])
def lpnewpwd():
    if not session.get('otp_verified_for_reset') or 'seslpemail' not in session:
        flash("Unauthorized access.", 'warning')
        return redirect(url_for('auth.lostpassword'))

    if request.method == 'POST':
        npwd = request.form.get('npwd')
        cpwd = request.form.get('cpwd')
        slpemail = session.get('seslpemail')

        if npwd == cpwd:
            # Restored to the scrypt standard
            clean_npwd = npwd.strip()
            hashed_npwd = generate_password_hash(clean_npwd, method='scrypt')
            
            cur = mysql.connection.cursor()
            cur.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_npwd, slpemail))
            mysql.connection.commit()
            cur.close()

            session.pop('seslpemail', None)
            session.pop('otp_verified_for_reset', None)

            flash('Your password was successfully changed. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash("Passwords do not match.", 'danger')

    return render_template('lpnewpwd.html')

@auth_bp.route('/changepassword', methods=["POST"])
def changePassword():
    if 'logged_in' not in session:
        flash('You must be logged in to change your password.', 'danger')
        return redirect(url_for('auth.login'))

    oldPassword = request.form.get('oldpassword')
    newPassword = request.form.get('newpassword')
    confirmPassword = request.form.get('confirmpassword') 

    redirect_target = 'student.student_index' if session.get('user_role') == 'student' else 'professor.professor_index'

    if newPassword != confirmPassword:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for(redirect_target))

    cur = mysql.connection.cursor()
    results = cur.execute('SELECT password FROM users WHERE email = %s AND uid = %s', (session['email'], session['uid']))
    
    if results > 0:
        stored_password_hash = cur.fetchone()['password']
        
        # Verify old password securely
        if check_password_hash(stored_password_hash, oldPassword.strip()) or stored_password_hash == oldPassword.strip():
            # Restored to the scrypt standard
            hashed_newPassword = generate_password_hash(newPassword.strip(), method='scrypt')
            cur.execute("UPDATE users SET password = %s WHERE email = %s AND uid = %s", (hashed_newPassword, session['email'], session['uid']))
            mysql.connection.commit()
            flash('Password changed successfully.', 'success')
        else:
            flash("Incorrect current password.", 'danger')
            
    cur.close()
    return redirect(url_for(redirect_target))