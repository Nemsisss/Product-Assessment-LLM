# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11


# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

EXPOSE 8502

COPY ./requirements.txt /app/requirements.txt

RUN \
  # Cleanup unnecessary package manager cache
  apt-get clean && \
  # Remove temporary files
  rm -rf /tmp/* /var/tmp/* && \
  # Clear package manager lists
  rm -rf /var/lib/apt/lists/*

# RUN CMAKE_ARGS="-DLLAMA_METAL=on" FORCE_CMAKE=1 pip install --upgrade --force-reinstall llama-cpp-python --no-cache-dir

# RUN apt update && apt install -y libopenblas-dev ninja-build build-essential
# RUN CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" FORCE_CMAKE=1 pip install --upgrade --force-reinstall llama-cpp-python --no-cache-dir


RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U spacy
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt


WORKDIR /app
COPY . /app

# Install pip requirements
# COPY requirements.txt .

ENTRYPOINT [ "streamlit", "run" , "--server.port=8502", "--server.address=0.0.0.0"]
CMD [ "main.py", "--server.headless", "true", "--server.fileWatcherType", "none", "--browser.gatherUsageStats", "false"]

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# # During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# CMD ["python", "main.py"]
