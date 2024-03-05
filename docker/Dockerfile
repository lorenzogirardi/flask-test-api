FROM lgirardi/lg-flaskimg-alpine:edge
RUN touch /var/log/app.log
RUN adduser -D worker
RUN chown -R worker:worker /var/log/app.log
USER worker
WORKDIR /home/worker
COPY --chown=worker:worker requirements.txt requirements.txt
COPY --chown=worker:worker . . 
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["ddtrace-run", "python3", "app.py"]

