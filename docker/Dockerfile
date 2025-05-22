# Build stage for compiling dependencies
FROM python:3.9-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers python3-dev

# Set up working directory
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install dependencies with compilation support
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Final stage - runtime container
FROM lgirardi/lg-flaskimg-alpine:edge

# Environment variables
ENV US=worker
ENV GP=$US-group
ENV UID=10001
ENV GID=10000

# Create log file
RUN touch /var/log/app.log

# Add user and group
RUN addgroup \
    --gid "$GID" \
    "$GP" \
&&  adduser \
    --disabled-password \
    --ingroup "$GP" \
    -D \
    --uid "$UID" \
    $US

# Set permissions
RUN chown -R $UID:$UID /var/log/app.log

# Copy pre-built wheels from builder stage
COPY --from=builder /wheels /wheels

# Switch to non-root user
USER $US
WORKDIR /home/$US

# Copy application files
COPY --chown=$US:$US requirements.txt .
COPY --chown=$US:$US . .
COPY . /app
WORKDIR /app

# Install dependencies from wheels (no compilation needed)
RUN pip install --user --no-index --find-links=/wheels -r requirements.txt

# Install ddtrace separately
RUN pip install --user ddtrace==3.3.0 || echo "ddtrace installation skipped"

# Set PATH
ENV PATH="/home/$US/.local/bin:${PATH}" 

# Run the application
CMD ["python3", "app.py"]
