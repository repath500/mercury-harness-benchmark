# Starting from the base image provided by FeatBench
FROM ghcr.io/kndy666/featbench_stanfordnlp_dspy:7964

# Clone the repository and checkout the base commit. Then, clean up git history and remove the remote origin to prevent cheating.
RUN git clone https://github.com/stanfordnlp/dspy.git /testbed

WORKDIR /testbed

RUN git checkout 75c82ac471654464f6c298fc50c8826255f9e994 && \
    git for-each-ref --format="%(refname:short)" refs/heads/ | xargs -r git branch -D && \
    git checkout -b main && \
    git reflog expire --expire=now --all && \
    git gc --prune=now && \
    git remote remove origin

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
RUN mkdir -p /logs

# Run instance-specific setup commands, if any
# dspy-7964: install as editable - the image is missing this
RUN pip install -e .
