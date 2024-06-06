FROM python:latest

COPY . /workspace
WORKDIR /workspace

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT [ "python", "main.py" ]
