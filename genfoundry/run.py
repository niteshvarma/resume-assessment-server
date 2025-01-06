# run.py

import os
from genfoundry import create_app

# Determine the configuration to use (default is 'default')
#config_name = os.getenv('FLASK_CONFIG', 'default')

# Create the app with the specified configuration
#app = create_app(config_name)
app = create_app('development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)