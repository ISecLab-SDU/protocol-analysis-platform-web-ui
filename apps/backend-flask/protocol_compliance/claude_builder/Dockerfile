FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GLLVM_REPO=https://github.com/SRI-CSL/gllvm.git
ARG GLLVM_REF=master

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        clang-12 \
        clang-14 \
        cmake \
        curl \
        file \
        git \
        gnupg2 \
        golang-1.18-go \
        libclang-14-dev \
        libcurl4-openssl-dev \
        libsqlite3-dev \
        libssl-dev \
        llvm-12 \
        llvm-14 \
        llvm-14-dev \
        make \
        ninja-build \
        pkg-config \
        python3-pip \
        python3.10 \
        python3.10-venv \
        tree \
        tshark \
        wget \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/go/bin:/usr/lib/go-1.18/bin:/usr/lib/llvm-14/bin:/usr/local/bin:${PATH}"

RUN git clone --depth 1 --branch "${GLLVM_REF}" "${GLLVM_REPO}" /opt/src/gllvm \
    && cd /opt/src/gllvm \
    && GOBIN=/usr/local/bin /usr/lib/go-1.18/bin/go install ./cmd/...

RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/clang-14 /usr/local/bin/clang \
    && ln -sf /usr/bin/clang++-14 /usr/local/bin/clang++ \
    && ln -sf /usr/bin/clang-cpp-14 /usr/local/bin/clang-cpp \
    && mkdir -p /workspace /out /usr/local/lib/protocolguard-builder

COPY pg-claude-builder /usr/local/bin/pg-claude-builder
RUN chmod +x /usr/local/bin/pg-claude-builder

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/pg-claude-builder"]
