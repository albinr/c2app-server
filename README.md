![Logo](static/images/icon.ico)

# C2 Security Application Server

## Introduction

The C2 Security Application Server is the backend component of the C2 system designed for monitoring and managing endpoint devices. It facilitates communication between the admin interface and client devices, allowing for device monitoring, command execution, file management, and watchlist control. The server provides RESTful API endpoints for device management and uses WebSockets for real-time communication.

## Showcase
Below is a screenshot of the server ui:

![Server UI](static/images/showcase.png)


## How to Use

### Prerequisites

Ensure you have the following dependencies installed:
- Python 3.10 or higher
- Quart framework and other dependencies (use the provided `requirements.txt` file)

Install dependencies with:

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## Test
Unit tests can be run using the built-in unittest module. Make sure all dependencies are installed, and then execute:

```bash
python3 -m unittest discover -s tests
```
This will discover and run all available tests and provide a summary of any issues.

Ensure all dependencies are installed and correctly set up before running tests.

## Run
To run the server, use:

```bash
source venv/bin/activate
```
and then:

```bash
python3 server.py
```

The server should now be accessible through "http://localhost:5000"

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
