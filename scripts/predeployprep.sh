#!/bin/sh

echo '[1] Loading azd .env file from current environment'
while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

echo '[2] Creating python virtual environment "scripts/.venv"'
python -m venv scripts/.venv 2>/dev/null || python3 -m venv scripts/.venv 2>/dev/null
source ./scripts/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install certifi


echo '[3] Registering Zscaler certificates'
cat zscaler_root_ca.pem >> $(python -m certifi)
export CERT_PATH=$(python -m certifi)
export SSL_CERT_FILE=${CERT_PATH}
export REQUESTS_CA_BUNDLE=${CERT_PATH}
python -m pip config set global.cert $CERT_PATH

echo '[4] Installing dependencies from "requirements.txt" into virtual environment'
python -m pip install -r scripts/requirements.txt
python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
python -m spacy download en_core_web_sm

echo '[5] Clean up output folder'
rm -f output/*.json

echo '[6] Preparing PDF documents'
python ./scripts/prepdocs.py 'data/' --sourceformat 'pdf' -o 'output/' -p 'chunk' -v

echo '[7] Preparing HTML documents'
python ./scripts/prepdocs.py 'data/' --sourceformat 'html' -o 'output/' -p 'chunk' -v

echo '[8] Running "prepdocs.py" to create the index in the search service'
python ./scripts/prepdocs.py 'data/' -o 'output/' -p 'index' -v