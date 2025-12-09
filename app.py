from flask import Flask
from routes.users import users_bp
from routes.receipts import receipts_bp
from routes.expenses import expenses_bp
from routes.bills import bills_bp

app = Flask(__name__)

# Register the blueprints
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(receipts_bp, url_prefix='/receipts')
app.register_blueprint(expenses_bp, url_prefix='/expenses')
app.register_blueprint(bills_bp, url_prefix='/bills')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
