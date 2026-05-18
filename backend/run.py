"""Flask development entry point."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

flask_env = os.environ.get('FLASK_ENV', 'development')
app = create_app(flask_env)

if __name__ == '__main__':
    debug = flask_env == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug)
