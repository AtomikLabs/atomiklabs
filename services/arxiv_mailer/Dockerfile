FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum install -y \
    gcc \
    python3-devel \
    && yum clean all

# Set up working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Create requirements file first
COPY services/arxiv_mailer/requirements.txt ./
COPY services/data_layer /tmp/data_layer/

# Install requirements and the data_layer package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /tmp/data_layer/ && \
    rm -rf /tmp/data_layer

# Copy the function code
COPY services/arxiv_mailer/src/* ./

# Verify package installation
RUN python -c "import atomiklabs_data; print('Successfully imported atomiklabs_data')"

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command
CMD ["mailer.lambda_handler"] 