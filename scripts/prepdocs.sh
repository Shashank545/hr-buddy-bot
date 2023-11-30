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
./scripts/.venv/bin/python -m pip install --upgrade pip
./scripts/.venv/bin/python -m pip install certifi

echo '[3] Registering Zscaler certificates'
cat zscaler_root_ca.pem >> $(./scripts/.venv/bin/python -m certifi)
export CERT_PATH=$(./scripts/.venv/bin/python -m certifi)
export SSL_CERT_FILE=${CERT_PATH}
export REQUESTS_CA_BUNDLE=${CERT_PATH}
./scripts/.venv/bin/python -m pip config set global.cert $CERT_PATH