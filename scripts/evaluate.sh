#!/bin/sh

opt_acs="acs"
opt_approach="approach"
opt_llm="llm"
argerrormsg="$0: Usage: $0 [$opt_acs|$opt_approach|$opt_llm]"
if [ "$#" -ne 1 ]; then
    echo $argerrormsg
    exit 1
fi
target=$1

echo '[1] Loading azd .env file from current environment'
while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    if [ $key = AZURE_SEARCH_SERVICE ] || [ $key = AZURE_SEARCH_INDEX_IFRS ] || [ $key = AZURE_OPENAI_SERVICE ]; then
        export "$key=$value"
    fi
done <<EOF
$(azd env get-values)
EOF

echo '[2] Creating python virtual environment "scripts/.venv"'
python -m venv scripts/.venv 2>/dev/null || python3 -m venv scripts/.venv 2>/dev/null
./scripts/.venv/bin/python -m pip install --upgrade pip

echo '[3] Registering Zscaler certificates'
cat zscaler_root_ca.pem >> $(./scripts/.venv/bin/python -m certifi)
export CERT_PATH=$(./scripts/.venv/bin/python -m certifi)
export SSL_CERT_FILE=${CERT_PATH}
export REQUESTS_CA_BUNDLE=${CERT_PATH}
./scripts/.venv/bin/python -m pip config set global.cert $CERT_PATH

echo '[4] Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt

if [ $target = $opt_acs ]; then
    echo '[5] Running "evaluate_acs.py"'
    ./scripts/.venv/bin/python ./scripts/evaluate_acs.py \
        --search-service $AZURE_SEARCH_SERVICE \
        --index $AZURE_SEARCH_INDEX_IFRS \
        --search-options=bm25,semantic,vector,vector-bm25,vector-semantic \
        --top=3 \
        --openai-service $AZURE_OPENAI_SERVICE

elif [ $target = $opt_approach ]; then
    echo '[5] Running "evaluate_qa.py"'
    ./scripts/.venv/bin/python ./scripts/evaluate_qa.py \
        --approach-options 1,2,3,4 \
	    --llm-options gpt-4 \
        --search-option=vector-semantic \
        --top=3 \
        --temperature=0

elif [ $target = $opt_llm ]; then
    echo '[5] Running "evaluate_qa.py"'
    ./scripts/.venv/bin/python ./scripts/evaluate_qa.py \
        --approach-options 3 \
	    --llm-options gpt-35-turbo,gpt-4 \
        --search-option=vector-semantic \
        --top=3 \
        --temperature=0

else
    echo "$0: Unknown option '$target'. Choose option from {$opt_acs,$opt_approach,$opt_llm}"
fi
