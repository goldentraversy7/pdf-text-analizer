from flask import render_template, Blueprint, current_app, request, redirect, url_for, make_response, jsonify, session, flash
import smtplib
from itsdangerous import SignatureExpired, BadTimeSignature
import jwt
import datetime
from functools import wraps
from flask_bcrypt import Bcrypt
from app.mongo import get_db, get_user_info, update_user_info
from app.extension import s
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

users_bp = Blueprint('users', __name__)

load_dotenv()

client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
CONF_URL = os.getenv('GOOGLE_CONF_URL')

oauth = OAuth(current_app)
google = oauth.register(
    'google',
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def send_email_via_smtp(email, message):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    MESSAGE_SENDER = str(os.getenv('MESSAGE_SENDER'))
    MESSAGE_SENDER_APP_PASSWORD = str(os.getenv('MESSAGE_SENDER_APP_PASSWORD'))
    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER
    msg['To'] = email
    msg['Subject'] = "Verify your email"
    
    msg.attach(MIMEText(message, 'HTML')) 

    try:
        s.login(MESSAGE_SENDER, MESSAGE_SENDER_APP_PASSWORD)
        s.sendmail(MESSAGE_SENDER, email, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        s.quit()
    return


def create_user_token(email):
    return jwt.encode({
        'email': email,
        'exp': datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=8)
    }, current_app.config['FLASK_SECRET_KEY'], algorithm="HS256")

def user_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('user_token')
        if not token or 'user_info' not in session:
            return redirect(url_for('user.users.login_page'))
        try:
            data = jwt.decode(token, current_app.config['FLASK_SECRET_KEY'], algorithms=["HS256"])
            email = data['email']
            db = get_db()
            users_collection = db['users']
            current_user = users_collection.find_one({'email': data['email'], 'type': 'user'})
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return redirect(url_for('user.users.login_page'))
        new_token = create_user_token(email)
        response = make_response(f(current_user, *args, **kwargs))
        response.set_cookie('user_token', new_token, httponly=True)
        session.permanent = True
        session['user_info'] = current_user['email']
        return response
    return decorated

@users_bp.route('/')
def home():
    token = request.cookies.get('user_token')
    if not token or 'user_info' not in session:
        current_user = {}
    else:
        try:
            data = jwt.decode(token, current_app.config['FLASK_SECRET_KEY'], algorithms=["HS256"])
            email = data['email']
            
            db = get_db()
            users_collection = db['users']
            current_user = users_collection.find_one({'email': email, 'type': 'user'})
        except Exception as e:
            current_user = {}
    return render_template('landing.html', user=current_user)

@users_bp.route('/login')
def login_page():
    token = request.cookies.get('user_token')
    if token and 'user_info' in session:
        try:
            data = jwt.decode(token, current_app.config['FLASK_SECRET_KEY'], algorithms=["HS256"])
            db = get_db()
            users_collection = db['users']
            current_user = users_collection.find_one({'email': data['email'], 'type': 'user'})

            if current_user:
                session.permanent = True
                session['user_info'] = current_user['email']
                return redirect(url_for('user.users.home'))
            else:
                raise Exception("User not found")
        except Exception as e:
            flash(e, 'danger')
            return render_template('user_login.html')
    return render_template('user_login.html')

@users_bp.route('login/users', methods=['POST'])
def login_user():
    if request.method == 'POST':
        bcrypt = Bcrypt(current_app)
        email = request.form.get('email')
        pwd = request.form.get('pwd')
        db = get_db()
        users_collection = db['users']

        user = users_collection.find_one({'email': email, 'type': 'user'})
        if not user or not bcrypt.check_password_hash(user['pwd'], pwd):
            return jsonify({'message': 'Invalid username or password!'}), 401
        
        if user['verify'] == False:
            return jsonify({'message': 'Email verification is needed to proceed.'}), 401
        
        token = jwt.encode({
                'email': email,
                'exp': datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1)
            }, current_app.config['FLASK_SECRET_KEY'], algorithm="HS256")
        
        response = jsonify({'message': 'Login successfully'})
        response.set_cookie('user_token', token, httponly=True)
        session.permanent = True
        session['user_info'] = user['email']
        flash("Welcome back! You've logged in successfully.", 'success')
        return response
    
@users_bp.route('logout', methods=['GET', 'POST'])
def logout_user():
    response = make_response(redirect(url_for('user.users.login_page')))
    response.delete_cookie('user_token')
    session.pop('user_info', None)
    return response

#Routes for login
@users_bp.route('/login/google')
def userGoogleLogin():
    return oauth.google.authorize_redirect(redirect_uri=url_for('user.users.userAuthorize', _external=True))

@users_bp.route('/google/authorize')
def userAuthorize():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        db = get_db()
        collection = db['users']
        current_user = collection.find_one({'email': user_info['email'], 'type': 'user'})
        if not current_user:
            collection.insert_one({
                'email': user_info['email'],
                'type': 'user',
                'given_name': user_info['given_name'],
                'family_name': user_info['family_name'],
                'picture': user_info['picture'],
                'verify': True,
                'createdAt': datetime.datetime.now()
            })
        new_token = create_user_token(user_info['email'])
        response = make_response(redirect(url_for('user.users.home')))
        response.set_cookie('user_token', new_token, httponly=True)
        session.permanent = True
        session['user_info'] = current_user['email']
        flash("Welcome back! You've logged in successfully.", 'success')
        return response
    except Exception as e:
        flash("Something went wrong", 'danger')
        return redirect('/')
    
@users_bp.route('/register')
def userRegisterPage():
    return render_template('user_register.html')

@users_bp.route('register/users', methods=['POST'])
def register_user():
    if request.method == 'POST':
        bcrypt = Bcrypt(current_app)
        givenName = request.form.get('givenName')
        familyName = request.form.get('familyName')
        email = request.form.get('email')
        pwd = request.form.get('pwd')
        db = get_db()
        users_collection = db['users']


        user = users_collection.find_one({'email': email, 'type': 'user'})
        if user:
            return jsonify({'message': 'The email exists'}), 400
        
        token = s.dumps(email, salt='email-confirm')
        link = url_for('user.users.confirm_email', token=token, _external=True)
        html_content = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 5px; max-width: 600px; margin: 20px auto; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);">
            <div style="text-align: center; padding: 10px 0; border-bottom: 1px solid #dddddd;">
                <h1>Email Verification</h1>
            </div>
            <div style="padding: 20px; text-align: center;">
                <p>Hi there,</p>
                <p>Thank you for registering! Please click the button below to verify your email address:</p>
                <p>
                    <a href="{link}" style="background-color: #007BFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verify Email
                    </a>
                </p>
                <p>If you did not sign up for this account, you can safely ignore this email.</p>
            </div>
            <div style="margin-top: 20px; font-size: 12px; color: #777777; text-align: center;">
                <p>&copy; TextAnalyzer All Rights Reserved</p>
            </div>
        </div>
        """
        send_email_via_smtp(email, html_content)
        users_collection.insert_one({
            'email': email,
            'type': 'user',
            'pwd': bcrypt.generate_password_hash(pwd).decode('utf-8'),
            'given_name': givenName,
            'family_name': familyName,
            'verify': False,
            'createdAt': datetime.datetime.now()
        })
        flash("You're registered! Check your inbox for a confirmation email.", 'success')
        return jsonify({'message': 'Successfully registered'}), 200
    
@users_bp.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)

        db = get_db()
        users_collection = db['users']

        query_filter = {'email' : email, 'type': 'user'}
        update_operation = { '$set' : 
            { 
                'verify': True
            }
        }
        users_collection.update_one(query_filter, update_operation)

        flash('Your email has been verified successfully!', 'success')
    except SignatureExpired:
        flash('The confirmation link has expired.', 'danger')
        return redirect(url_for('user.users.userRegisterPage'))
    except BadTimeSignature:
        flash('The confirmation link is invalid.', 'danger')
        return redirect(url_for('user.users.userRegisterPage'))
    except Exception:
        flash('Something went wrong', 'danger')
    
    return redirect(url_for('user.users.login_page'))

@users_bp.route('/profile')
def userProfilePage():
    if 'user_info' not in session:
        return redirect(url_for('user.users.login_page'))
    useremail = session['user_info']
    user = get_user_info(useremail,'user')
    return render_template('user_profile.html', user=user)

@users_bp.route('/profile/save', methods=['POST'])
def userProfileSave():
    if 'user_info' not in session:
        flash('We need you to log in to proceed.', 'warning')
        return redirect(url_for('user.users.login_page'))
    
    if request.method == 'POST':
        try:
            bcrypt = Bcrypt(current_app)
            user_email = session['user_info']
            update_data = {}
            update_data['given_name'] = request.form.get('given_name')
            update_data['family_name'] = request.form.get('family_name')
            update_data['phone_number'] = request.form.get('phone_number')
            update_data['address'] = request.form.get('address')
            old_pwd = request.form.get('old_pwd')
            new_pwd = request.form.get('new_pwd')

            user = get_user_info(user_email, 'user')
            
            if (old_pwd or new_pwd) and not bcrypt.check_password_hash(user['pwd'], old_pwd):
                return jsonify({'message': 'The current password you entered is incorrect.'}), 400
            if old_pwd:
                update_data['pwd'] = bcrypt.generate_password_hash(new_pwd).decode('utf-8')
            
            update_user_info(user_email, 'user', update_data)
            return jsonify({'message': 'success'}), 200
        except Exception as e:
            return jsonify({'message': 'Something went wrong'}), 400