# Dockerfile

FROM python:3.12

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    echo "export PATH=$HOME/.local/bin:$PATH" >> ~/.bashrc

WORKDIR /app

COPY ./pyproject.toml ./poetry.lock /app/

RUN /root/.local/bin/poetry install

COPY . /app

CMD ["/root/.local/bin/poetry", "run", "python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
