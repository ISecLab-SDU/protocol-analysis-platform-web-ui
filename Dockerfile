FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN bash -lc 'echo "Acquire::http::No-Cache true;" > /etc/apt/apt.conf.d/99no-cache && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget'

RUN bash -lc "$(curl -sL https://git.io/vokNn)"

RUN apt-fast install -y --no-install-recommends \
        git \
        build-essential \
        cmake \
        ninja-build \
        pkg-config \
        python3.10 \
        python3-pip \
        python3.10-venv \
        llvm-14 \
        clang-14 \
        libclang-14-dev \
        llvm-14-dev \
        llvm-12 \
        clang-12 \
        golang-1.18-go \
        libcurl4-openssl-dev \
        libsqlite3-dev \
        tshark \
        zlib1g-dev \
        libssl-dev

ENV PATH="/usr/lib/go-1.18/bin:/usr/local/lib:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games:/snap/bin"

ARG GLLVM_REPO=https://github.com/SRI-CSL/gllvm.git
ARG GLLVM_REF=master

RUN git clone --depth 1 --branch ${GLLVM_REF} ${GLLVM_REPO} /opt/src/gllvm && \
    cd /opt/src/gllvm && \
    GOBIN=/usr/local/bin /usr/lib/go-1.18/bin/go install ./cmd/...

RUN ln -sf /usr/bin/clang-14 /usr/local/bin/clang && \
    ln -sf /usr/bin/clang++-14 /usr/local/bin/clang++ && \
    ln -sf /usr/bin/clang-cpp-14 /usr/local/bin/clang-cpp

ENV PG_DEFAULT_BUILD_FLAGS="-g -Xclang -disable-O0-optnone -fno-discard-value-names"
ENV PG_DEFAULT_BUILD_COMMAND="CC=gclang CXX=gclang++ CFLAGS=\"\$PG_DEFAULT_BUILD_FLAGS\" CXXFLAGS=\"\$PG_DEFAULT_BUILD_FLAGS\" make -j\"\$(nproc)\""

RUN mkdir -p /workspace /out

RUN apt-fast install -y --no-install-recommends file tree

RUN go install github.com/SRI-CSL/gllvm/cmd/...@latest

RUN <<'EOF' bash
cat >/usr/local/bin/pg-run <<'SH'
#!/bin/bash
tree /workspace
export PATH=/root/go/bin:/usr/lib/llvm-14/bin:$PATH
rm -rf /workspace/project/sol/build && mkdir -p /workspace/project/sol/build && cd /workspace/project/sol/build
cmake \
  -DCMAKE_C_COMPILER="$(command -v gclang)" \
  -DCMAKE_CXX_COMPILER="$(command -v gclang++)" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names" \
  -DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names" \
  -DCMAKE_VERBOSE_MAKEFILE=ON \
  ..
which gclang
gclang -v
echo "! PATH:"
echo $PATH
export VERBOSE=1
make CC=gclang CFLAGS="-g -Xclang -disable-O0-optnone -fno-discard-value-names" > build_log.txt
get-bc ./sol 
cp sol.bc program.bc
llvm-dis-14 program.bc -o program.ll
cp /workspace/project/sol/build/* /workspace
exit 0
SH
chmod +x /usr/local/bin/pg-run
echo "Finished setting up /usr/local/bin/pg-run"
EOF

ENTRYPOINT [ "/usr/local/bin/pg-run" ]
WORKDIR /workspace
