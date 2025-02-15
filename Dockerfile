FROM python:3.12

COPY . /workspace
WORKDIR /workspace

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT [ "python", "main.py" ]
