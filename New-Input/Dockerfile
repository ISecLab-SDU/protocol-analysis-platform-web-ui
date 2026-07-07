
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    xz-utils \
    make \
    cmake \
    gcc \
    g++ \
    libc6-dev \
    libsqlite3-dev \
    libssl-dev \
    pkg-config \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/llvm/llvm-project/releases/download/llvmorg-16.0.6/clang+llvm-16.0.6-x86_64-linux-gnu-ubuntu-22.04.tar.xz \
    && tar -xf clang+llvm-16.0.6-x86_64-linux-gnu-ubuntu-22.04.tar.xz -C /usr/local --strip-components=1 \
    && rm clang+llvm-16.0.6-x86_64-linux-gnu-ubuntu-22.04.tar.xz

RUN ln -sf /usr/local/bin/clang /usr/local/bin/gclang

WORKDIR /workspace

COPY sol.tar /workspace/sol.tar

RUN tar -xf sol.tar -C /workspace

COPY config.toml /workspace/config.toml
COPY rule_config.json /workspace/inputs/rules.json

RUN mkdir -p /workspace/project/sol/build

WORKDIR /workspace/project/sol

RUN cmake -S . -B build \
    -DCMAKE_C_COMPILER=gclang \
    -DCMAKE_C_FLAGS="-g -Xclang -disable-O0-optnone -fno-discard-value-names" \
    && cmake --build build -- VERBOSE=1 2>&1 | tee /workspace/project/sol/build/build_log.txt

RUN cp /workspace/project/sol/build/sol.bc /workspace/project/sol/build/sol_ssa.bc

RUN apt-get update && apt-get install -y --no-install-recommends \
    llvm-16-dev \
    && rm -rf /var/lib/apt/lists/*

RUN /usr/local/bin/opt -S -passes=mem2reg /workspace/project/sol/build/sol.bc -o /workspace/project/sol/build/sol_ssa.ll

RUN cp /workspace/project/sol/build/sol_ssa.ll /workspace/project/sol/build/sol.ll

RUN echo "Build complete" > /workspace/build_complete.txt

CMD ["/bin/bash"]
