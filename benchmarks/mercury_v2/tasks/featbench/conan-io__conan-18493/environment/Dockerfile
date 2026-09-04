# Starting from the base image provided by FeatBench
FROM ghcr.io/kndy666/featbench_conan-io_conan:18493

# Clone the repository and checkout the base commit. Then, clean up git history and remove the remote origin to prevent cheating.
RUN git clone https://github.com/conan-io/conan.git /testbed

WORKDIR /testbed

RUN git checkout ff5c4ffcefa632e11474221b014b23b0c9a3de22 && \
    git for-each-ref --format="%(refname:short)" refs/heads/ | xargs -r git branch -D && \
    git checkout -b main && \
    git reflog expire --expire=now --all && \
    git gc --prune=now && \
    git remote remove origin

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
RUN mkdir -p /logs

# Run instance-specific setup commands, if any
# Conan cmake environment setup
RUN cmake_bin=$(which cmake 2>/dev/null) && \
    [ -n "$cmake_bin" ] && \
    python3 -c "import re; f=open('test/conftest.py'); c=f.read(); f.close(); paths=re.findall(r\"'Linux': ['\\\"]([^'\\\"]+)['\\\"]\", c); print('\\n'.join(paths))" | while read path; do \
    [ "$path" != "$(dirname $cmake_bin)" ] && [ "$path" != "/usr/share/cmake-3.15.7/bin" ] && mkdir -p "$path" && ln -sf "$cmake_bin" "$path/cmake"; \
    done && \
    cmake_ver=$(cmake --version 2>/dev/null | head -1) && \
    if ! echo "$cmake_ver" | grep -q 'cmake version 3\.15'; then \
      wget -q https://cmake.org/files/v3.15/cmake-3.15.7-Linux-x86_64.sh -O /tmp/cmake-3.15.sh && \
      chmod +x /tmp/cmake-3.15.sh && \
      /tmp/cmake-3.15.sh --prefix=/usr/local --skip-license && \
      mkdir -p /usr/share/cmake-3.15.7/bin && \
      ln -sf /usr/local/bin/cmake /usr/share/cmake-3.15.7/bin/cmake; \
    else \
      mkdir -p /usr/share/cmake-3.15.7/bin && ln -sf "$cmake_bin" "/usr/share/cmake-3.15.7/bin/cmake"; \
    fi || true
