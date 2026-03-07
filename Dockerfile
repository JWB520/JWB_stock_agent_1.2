FROM python:3.11-slim

WORKDIR /app

RUN pip install pdm

COPY pyproject.toml pdm.lock* ./
RUN pdm install --no-self

COPY . .

CMD ["pdm", "run", "python", "-m", "agent.main"]
