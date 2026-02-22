FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install common language toolchains the agent might choose
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://go.dev/dl/go1.23.6.linux-amd64.tar.gz | tar -C /usr/local -xzf - && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go

ENV PATH="/usr/local/go/bin:${PATH}"

RUN mkdir -p /workspace /logs /logs/verifier /logs/agent /logs/artifacts /tests
RUN chmod -R 777 /workspace /logs

WORKDIR /workspace

# Copy mock server into the image
COPY tests/mock_server.py /tests/mock_server.py
COPY tests/conformance/ /tests/conformance/
COPY tests/test.sh /tests/test.sh
COPY tests/score.py /tests/score.py
