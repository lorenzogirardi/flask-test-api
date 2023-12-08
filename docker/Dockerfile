FROM python:3.10-alpine
COPY . /app
WORKDIR /app
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app.py"]

