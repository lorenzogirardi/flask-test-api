# python rest api test application

This is a sample Python REST API application built with Flask.

## Features

-   **RESTful API:** Provides a RESTful API for managing contexts.
-   **OpenAPI v3:** Includes Swagger documentation for the API.
-   **Structured Logging:** Logs are in JSON format for easy parsing.
-   **Datadog Integration:** Integrated with Datadog for tracing and metrics.
-   **Prometheus Metrics:** Exposes a `/metrics` endpoint for Prometheus.
-   **Health Check:** Provides a `/health` endpoint for Kubernetes probes.
-   **Containerized:** Runs in a Docker container.

## Running the Application

### Docker

To build and run the application with Docker:

```bash
docker build -t pytbak:latest -f docker/Dockerfile .
docker run -p 5000:5000 pytbak:latest
```

The application will be available at `http://localhost:5000`.

### Kubernetes

To deploy the application to Kubernetes:

```bash
kubectl apply -f kubernetes/
```

Remember to configure your ingress controller to route traffic to the `pytbak-svc` service in the `pytbak` namespace.

## API Documentation

The API documentation is available at the `/apidocs` endpoint when the application is running.

| HTTP Method | URI               | Action                     |
| ----------- | ----------------- | -------------------------- |
| GET         | /api/contexts     | Retrieve list of contexts  |
| GET         | /api/contexts/{id} | Retrieve a context         |
| POST        | /api/contexts     | Create a new context       |
| PUT         | /api/contexts/{id} | Update an existing context |
| DELETE      | /api/contexts/{id} | Delete a context           |
