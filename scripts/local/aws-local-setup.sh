#!/bin/bash

# Add LocalStack AWS CLI alias
echo '# LocalStack AWS CLI alias' >> ~/.bashrc
echo 'alias lawslocal="aws --endpoint-url=http://localhost:4566"' >> ~/.bashrc

# Source the updated bashrc
source ~/.bashrc

echo "LocalStack AWS CLI alias 'lawslocal' has been added to your ~/.bashrc"
echo "You can now use 'lawslocal' instead of 'aws --endpoint-url=http://localhost:4566'"
echo "For example: lawslocal s3 ls"
