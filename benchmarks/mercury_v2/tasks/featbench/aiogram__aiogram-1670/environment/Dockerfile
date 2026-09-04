# Starting from the base image provided by FeatBench
FROM ghcr.io/kndy666/featbench_aiogram_aiogram:1670

# Clone the repository and checkout the base commit. Then, clean up git history and remove the remote origin to prevent cheating.
RUN git clone https://github.com/aiogram/aiogram.git /testbed

WORKDIR /testbed

RUN git checkout 25e9127db9004c9c49ca46bdf5297682fac71fbb && \
    git for-each-ref --format="%(refname:short)" refs/heads/ | xargs -r git branch -D && \
    git checkout -b main && \
    git reflog expire --expire=now --all && \
    git gc --prune=now && \
    git remote remove origin

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
RUN mkdir -p /logs

# Run instance-specific setup commands, if any

