#!/bin/sh

installPackages="--install-packages"

######################
# Load env variables #
######################
echo "$0: [STEP 1/6] Loading azd .env file from current environment"
while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF
if [ $? -ne 0 ]; then
    echo "Failed to load environment variables from azd environment"
    exit $?
fi

##################
# Start frontend #
##################
cd frontend/

if [ "$1" = "$installPackages" ]; then
    echo "$0: [STEP 2/6] Install node packages"
    npm ci
    npm audit fix
fi

echo "$0: [STEP 3/6] Starting frontend development server"
lsof -i :5173 -t | xargs kill
npm run dev &

#################
# Start backend #
#################
cd ../backend

if [ "$1" = "$installPackages" ]; then
    echo "$0: [STEP 4/6] Creating python virtual environment 'backend/backend_env'"
    python -m venv backend_env

    echo "$0: [STEP 5/6] Restoring backend python packages"
    ./backend_env/bin/python -m pip install -r requirements.txt
    ./backend_env/bin/python -m spacy download en_core_web_sm
    if [ $? -ne 0 ]; then
        echo "Failed to restore backend python packages"
        exit $?
    fi
fi

echo "$0: [STEP 6/6] Starting backend"
export FLASK_DEBUG=1
./backend_env/bin/python ./app.py
if [ $? -ne 0 ]; then
    echo "Failed to start backend"
    exit $?
fi
