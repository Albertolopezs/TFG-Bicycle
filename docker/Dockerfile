FROM ubuntu
ENV FLASK_APP app.py
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["flask", "run"]