FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GLLVM_REPO=https://github.com/SRI-CSL/gllvm.git
ARG GLLVM_REF=master
ARG CLAUDE_CODE_VERSION=2.1.207

COPY --chmod=0755 apt-fast-downloader /usr/local/bin/apt-fast-downloader

# Keep package indexes and downloaded archives outside image layers so interrupted
# builds and Dockerfile changes can reuse them. The proxy build args supported by
# Docker are intentionally not persisted with ENV directives.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    printf '%s\n' \
        'Acquire::Retries "20";' \
        'Acquire::http::Timeout "60";' \
        'Acquire::https::Timeout "60";' \
        'Acquire::ftp::Timeout "60";' \
        'Acquire::Queue-Mode "host";' \
        'APT::Keep-Downloaded-Packages "true";' \
        'Binary::apt::APT::Keep-Downloaded-Packages "true";' \
        > /etc/apt/apt.conf.d/80protocolguard-network \
    && for attempt in $(seq 1 20); do \
        apt-get update && break; \
        if [ "${attempt}" = 20 ]; then exit 1; fi; \
        rm -rf /var/lib/apt/lists/partial; \
        mkdir -p /var/lib/apt/lists/partial; \
        sleep "$((attempt * 2))"; \
    done \
    && apt-get install -y --no-install-recommends ca-certificates curl wget \
    && sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
        /etc/apt/sources.list \
    && curl --fail --show-error --location \
        --retry 20 --retry-all-errors --retry-delay 2 --connect-timeout 30 \
        https://git.io/vokNn | bash \
    && sed -i \
        -e 's/^_MAXNUM=.*/_MAXNUM=16/' \
        -e 's/^_MAXCONPERSRV=.*/_MAXCONPERSRV=16/' \
        -e 's/^_MINSPLITSZ=.*/_MINSPLITSZ=1M/' \
        -e 's/^_SPLITCON=.*/_SPLITCON=16/' \
        /etc/apt-fast.conf \
    && printf '%s\n' \
        'DOWNLOADBEFORE=true' \
        '_MAXNUM=16' \
        '_MAXCONPERSRV=16' \
        '_MINSPLITSZ=1M' \
        '_SPLITCON=16' \
        '_DOWNLOADER='\''aria2c --no-conf --continue=true --max-concurrent-downloads=${_MAXNUM} --max-connection-per-server=${_MAXCONPERSRV} --split=${_SPLITCON} --min-split-size=${_MINSPLITSZ} --stream-piece-selector=${_PIECEALGO} --input-file=${DLLIST} --connect-timeout=30 --timeout=60 --lowest-speed-limit=1K --max-tries=20 --retry-wait=3 --max-file-not-found=5 --file-allocation=none --auto-file-renaming=false --header "Accept: */*"'\''' \
        >> /etc/apt-fast.conf \
    && sed -i \
        -e '/^        eval "${_DOWNLOADER}"  # execute downloadhelper command$/c\        /usr/local/bin/apt-fast-downloader "$DLLIST" "$DLDIR" "$_MAXNUM" "$_MAXCONPERSRV" "$_SPLITCON" "$_MINSPLITSZ" "$_PIECEALGO" || exit 1' \
        -e '/^    "${_APTMGR}" "${APT_SCRIPT_WARNING\[@\]}" "\$@"$/ s/"\$@"/--no-download "$@"/' \
        /usr/local/bin/apt-fast

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    for attempt in $(seq 1 20); do \
        apt-fast update && break; \
        if [ "${attempt}" = 20 ]; then exit 1; fi; \
        rm -rf /var/lib/apt/lists/partial; \
        mkdir -p /var/lib/apt/lists/partial; \
        sleep "$((attempt * 2))"; \
    done \
    && apt-fast install -y --no-install-recommends \
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
        p7zip-full \
        pkg-config \
        python3-pip \
        python3.10 \
        python3.10-venv \
        tree \
        tshark \
        unzip \
        wget \
        zlib1g-dev

ENV PATH="/root/go/bin:/usr/lib/go-1.18/bin:/usr/lib/llvm-14/bin:/usr/local/bin:${PATH}"

RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/root/go/pkg/mod \
    git config --global http.lowSpeedLimit 1024 \
    && git config --global http.lowSpeedTime 120 \
    && for attempt in 1 2 3 4 5; do \
        git clone --depth 1 --branch "${GLLVM_REF}" "${GLLVM_REPO}" /opt/src/gllvm \
            && break; \
        rm -rf /opt/src/gllvm; \
        if [ "${attempt}" = 5 ]; then exit 1; fi; \
        sleep "$((attempt * 2))"; \
    done \
    && cd /opt/src/gllvm \
    && GOBIN=/usr/local/bin /usr/lib/go-1.18/bin/go install ./cmd/...

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    install -m 0755 -d /etc/apt/keyrings \
    && curl --fail --show-error --location \
        --retry 20 --retry-all-errors --retry-delay 2 --connect-timeout 30 \
        https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && for attempt in $(seq 1 20); do \
        apt-fast update && break; \
        if [ "${attempt}" = 20 ]; then exit 1; fi; \
        rm -rf /var/lib/apt/lists/partial; \
        mkdir -p /var/lib/apt/lists/partial; \
        sleep "$((attempt * 2))"; \
    done \
    && apt-fast install -y --no-install-recommends nodejs=20.*

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm config set fetch-retries 20 \
    && npm config set fetch-retry-mintimeout 2000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set maxsockets 32 \
    && npm install -g --include=optional --ignore-scripts=false \
        "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && node "$(npm root -g)/@anthropic-ai/claude-code/install.cjs" \
    && claude --version

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=20 \
        python3 -m pip install claude-agent-sdk==0.2.116

RUN ln -sf /usr/bin/clang-14 /usr/local/bin/clang \
    && ln -sf /usr/bin/clang++-14 /usr/local/bin/clang++ \
    && ln -sf /usr/bin/clang-cpp-14 /usr/local/bin/clang-cpp \
    && mkdir -p /workspace /out /usr/local/lib/protocolguard-builder

COPY pg-claude-builder pg_claude_builder_sdk.py claude_agent_events.py /usr/local/bin/
RUN chmod +x /usr/local/bin/pg-claude-builder /usr/local/bin/pg_claude_builder_sdk.py

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/pg-claude-builder"]
