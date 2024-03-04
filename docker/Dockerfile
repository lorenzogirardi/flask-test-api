FROM lgirardi/lg-flaskimg-alpine:edge
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["ddtrace-run", "python3", "app.py"]

