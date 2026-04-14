from flask import Blueprint, render_template

# Create the Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/calc')
def calc():
    return render_template('calc.html')

@main_bp.route('/faq')
def faq():
    return render_template('faq.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')