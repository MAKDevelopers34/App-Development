from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    app.run(
        debug=os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes'),
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', '5000')),
        threaded=True,
    )
