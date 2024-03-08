FROM lgirardi/lg-flaskimg-alpine:edge

ENV US=worker
ENV GP=$US-group
ENV UID=10001
ENV GID=10000

RUN touch /var/log/app.log

RUN addgroup \
    --gid "$GID" \
    "$GP" \
&&  adduser \
    --disabled-password \
    --ingroup "$GP" \
    -D \
    --uid "$UID" \
    $US

RUN chown -R $UID:$UID /var/log/app.log
USER $US
WORKDIR /home/$US
COPY --chown=$US:$US requirements.txt requirements.txt
COPY --chown=$US:$US . . 
COPY . /app
WORKDIR /app
RUN pip install --user -r requirements.txt
ENV PATH="/home/$US/.local/bin:${PATH}" 
CMD ["ddtrace-run", "python3", "app.py"]

