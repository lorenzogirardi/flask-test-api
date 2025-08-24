# Base image
FROM lgirardi/lg-flaskimg-alpine:edge

# Set user and group variables
ARG UID=10001
ARG GID=10001
ARG US=pytbak
ARG GP=pytbak

# Create user and group
RUN addgroup \
    --gid "$GID" \
    "$GP" \
&&  adduser \
    --disabled-password \
    --ingroup "$GP" \
    -D \
    --uid "$UID" \
    $US

# Set working directory
WORKDIR /app

# Create and set permissions for log file
RUN mkdir -p /var/log && \
    touch /var/log/app.log && \
    chown -R ${US}:${GP} /var/log

# Copy requirements and install dependencies
COPY --chown=${US}:${GP} requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=${US}:${GP} src/ /app

# Switch to non-root user
USER $US

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "-m", "app.main"]
