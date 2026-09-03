# Starting from the base image provided by FeatBench
FROM ghcr.io/kndy666/featbench_openai_openai-agents-python:508

# Clone the repository and checkout the base commit. Then, clean up git history and remove the remote origin to prevent cheating.
RUN git clone https://github.com/openai/openai-agents-python.git /testbed

WORKDIR /testbed

RUN git checkout e8f14da473775ca6a5f3d5208e21759bdeaf5040 && \
    git for-each-ref --format="%(refname:short)" refs/heads/ | xargs -r git branch -D && \
    git checkout -b main && \
    git reflog expire --expire=now --all && \
    git gc --prune=now && \
    git remote remove origin

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
RUN mkdir -p /logs

# Run instance-specific setup commands, if any

