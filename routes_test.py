
from flask import Blueprint, render_template

test_bp = Blueprint('test', __name__)

@test_bp.route('/test_doctype')
def test_doctype():
    return render_template('test_doctype.html')
