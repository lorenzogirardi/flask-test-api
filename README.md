# Python REST API Test Application

## 1. Overview

This project provides a sample Python REST API application built with Flask. It is designed to be a starting point for building robust, observable, and secure microservices. The application is containerized with Docker and ready to be deployed to Kubernetes.

The application serves as a simple "context" management service, allowing users to perform CRUD (Create, Read, Update, Delete) operations on context items.

### 1.1. Architecture

The application consists of the following components:

*   **Flask Application:** The core of the application, providing the REST API.
*   **Redis:** Used as a persistent data store for the context items.
*   **Docker:** The application is containerized for portability and ease of deployment.
*   **Kubernetes:** The project includes Kubernetes manifests for deploying the application to a cluster.
*   **Prometheus:** The application exposes a `/metrics` endpoint for Prometheus to scrape.
*   **Datadog:** The application is integrated with Datadog for distributed tracing.

## 2. Project Structure

```
.
├── docker
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src
│       └── app
│           ├── __init__.py
│           ├── business.py
│           ├── health.py
│           ├── main.py
│           ├── templates
│           │   └── index.html
│           └── utils.py
├── docker-compose.yml
├── kubernetes
│   ├── 01-ns-pytbak.yaml
│   ├── 02-svc-pytbak.yaml
│   ├── 03-ing-pytbak.yaml
│   ├── 04-dpl-pytbak.yaml
│   ├── 05-hpa-pytbak.yaml
│   └── 06-istio-pytbak.yaml
└── README.md
```

*   `docker/Dockerfile`: The Dockerfile for building the application image.
*   `docker/requirements.txt`: The Python dependencies.
*   `docker/src/app/`: The Python source code for the application.
    *   `main.py`: The main entry point for the Flask application, containing the API routes.
    *   `business.py`: The business logic for the application.
    *   `health.py`: The health check endpoint.
    *   `utils.py`: Utility functions, such as getting a Redis connection.
    *   `templates/index.html`: The HTML for the main page.
*   `docker-compose.yml`: A file for running the application locally with Docker Compose.
*   `kubernetes/`: Kubernetes manifests for deploying the application.

## 3. Sequence Diagram

The following diagram illustrates the request flow for creating a new context.

```mermaid
sequenceDiagram
    participant Client
    participant FlaskApp (main.py)
    participant BusinessLogic (business.py)
    participant Redis

    Client->>+FlaskApp (main.py): POST /api/contexts (json)
    FlaskApp (main.py)->>+BusinessLogic (business.py): create_new_context(data)
    BusinessLogic (business.py)->>+Redis: SET context:{id} {json}
    Redis-->>-BusinessLogic (business.py): OK
    BusinessLogic (business.py)-->>-FlaskApp (main.py): return context_object
    FlaskApp (main.py)-->>-Client: 201 CREATED (json)
```

## 4. Getting Started

### 4.1. Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/) (optional, for local development)
*   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) (for Kubernetes deployment)

### 4.2. Local Development

To run the application locally for development, you can use Docker Compose. This will start the application and a Redis container.

1.  **Build and start the containers:**

    ```bash
    docker-compose up --build -d
    ```

2.  **Access the application:**

    The application will be available at `http://localhost:5000/api/`.

3.  **View the logs:**

    ```bash
    docker-compose logs -f web
    ```

4.  **Stop the containers:**

    ```bash
    docker-compose down
    ```

### 4.3. Running in Kubernetes

To deploy the application to a Kubernetes cluster:

1.  **Apply the Kubernetes manifests:**

    ```bash
    kubectl apply -f kubernetes/
    ```

2.  **Access the application:**

    You will need to configure an Ingress controller to route traffic to the `pytbak-svc` service in the `pytbak` namespace. Refer to the `kubernetes/03-ing-pytbak.yaml` file for the Ingress configuration.

## 5. API Documentation

The API documentation is split into two sections:

-   **Application API:** Documentation for the main application endpoints is available at `/api/apidocs/`.
-   **Management API:** Documentation for the management and observability endpoints is available at `/mgmt/apidocs/`.

### 5.1. Endpoints

| HTTP Method | URI                | Action                     |
| ----------- | ------------------ | -------------------------- |
| GET         | `/api/contexts`    | Retrieve list of contexts  |
| GET         | `/api/contexts/{id}`| Retrieve a context         |
| POST        | `/api/contexts`    | Create a new context       |
| PUT         | `/api/contexts/{id}`| Update an existing context |
| DELETE      | `/api/contexts/{id}`| Delete a context           |
| GET         | `/api/fib/{n}`     | Calculate Fibonacci number |
| GET         | `/api/sleep/{n}`   | Sleep for n seconds        |
| GET         | `/api/count`       | Increment a counter        |
| GET         | `/api/redisping`   | Ping Redis                 |

### 5.2. Management Endpoints

| HTTP Method | URI                | Action                               |
| ----------- | ------------------ | ------------------------------------ |
| GET         | `/mgmt/health`     | Check application health             |
| GET         | `/mgmt/info`       | Display application info             |
| GET         | `/mgmt/env`        | Display whitelisted environment vars |
| GET         | `/mgmt/mappings`   | Display all URL mappings             |
| GET         | `/mgmt/threaddump` | Provide a thread dump                |
| GET         | `/mgmt/metrics`    | Link to the Prometheus metrics       |

## 6. API Usage Examples

The following examples assume the application is running at `http://localhost:5000`.

### 6.1. Create a new context

```bash
curl -i -X POST -H "Content-Type: application/json" \
    -d '{"title": "My First Context", "description": "This is a test context."}' \
    http://localhost:5000/api/contexts
```

The server will respond with the newly created context, including its unique ID.

```json
HTTP/1.1 201 CREATED
Content-Type: application/json
Content-Length: 123
...

{
  "description": "This is a test context.",
  "done": false,
  "id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "title": "My First Context"
}
```

### 6.2. Get all contexts

```bash
curl -i http://localhost:5000/api/contexts
```

### 6.3. Get a specific context

Replace `{context_id}` with the ID of the context you want to retrieve.

```bash
curl -i http://localhost:5000/api/contexts/{context_id}
```

### 6.4. Update a context

Replace `{context_id}` with the ID of the context you want to update.

```bash
curl -i -X PUT -H "Content-Type: application/json" \
    -d '{"done": true}' \
    http://localhost:5000/api/contexts/{context_id}
```

### 6.5. Delete a context

Replace `{context_id}` with the ID of the context you want to delete.

```bash
curl -i -X DELETE http://localhost:5000/api/contexts/{context_id}
```

The server will respond with a confirmation message.

```json
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 17
...

{
  "result": true
}
```

### 6.6. Calculate Fibonacci number

Note: The maximum value for this endpoint is 20,000.

```bash
curl -i http://localhost:5000/api/fib/10
```

### 6.7. Sleep for a number of seconds

```bash
curl -i http://localhost:5000/api/sleep/3
```

### 6.8. Increment a counter

```bash
curl -i http://localhost:5000/api/count
```

### 6.9. Ping Redis

```bash
curl -i http://localhost:5000/api/redisping
```

## 7. Key Features in Depth

### 7.1. Configuration

The application is configured using environment variables.

| Variable       | Description                  | Default     |
| -------------- | ---------------------------- | ----------- |
| `REDIS_HOST`   | The hostname of the Redis server. | `localhost` |
| `REDIS_PORT`   | The port of the Redis server.    | `6379`      |
| `REDIS_DB`     | The Redis database to use.       | `0`         |

### 7.2. Logging

The application uses structured logging in JSON format. This makes the logs easy to parse and analyze in a centralized logging system.

Example log entry:

```json
{
    "timestamp": "2023-10-27 10:00:00,000",
    "level": "INFO",
    "message": "127.0.0.1 - - [27/Oct/2023 10:00:00] \"GET /api/contexts HTTP/1.1\" 200 -"
}
```

### 7.3. Metrics

The application exposes a `/metrics` endpoint in Prometheus format. This can be scraped by a Prometheus server to monitor the application's performance.

### 7.4. Tracing

The application is integrated with Datadog for distributed tracing. The Kubernetes deployment is configured to enable Datadog tracing.

### 7.5. Security

The application is designed with security in mind.

*   **Container Security:** The Docker container is run with a restrictive security context in Kubernetes, including a non-root user, a read-only root filesystem, and no privileges.
*   **Input Validation:** The API performs basic validation of incoming requests.
*   **No Sensitive Information in Logs:** The logs are configured to avoid logging sensitive information.

## 8. Contributing

Contributions are welcome! Please follow these guidelines:

*   **Code Style:** Follow the PEP 8 style guide for Python.
*   **Pull Requests:** Create a pull request for any new features or bug fixes. Please provide a clear description of the changes.
*   **Testing:** Please add or update tests for any changes you make.
