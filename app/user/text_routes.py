from flask import render_template, Blueprint, session, jsonify, request, redirect, url_for, flash
from app.mongo import get_user_info

text_bp = Blueprint('text', __name__, url_prefix="text")

@text_bp.route('/')
def text_page():
    if 'user_info' not in session:
        return redirect(url_for('user.users.login_page'))
    current_user = session['user_info']
    user = get_user_info(current_user, 'user')
    return render_template('text.html', user=user)


@text_bp.route('/get')
def get_title():
    if 'user_info' not in session:
        return redirect(url_for('user.users.login_page'))
    current_user = session['user_info']
    title = request.args.get('title', '')
    return render_template('text.html', user=current_user, title=title)