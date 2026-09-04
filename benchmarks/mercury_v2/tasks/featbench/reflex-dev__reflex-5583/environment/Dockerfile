# Starting from the base image provided by FeatBench
FROM ghcr.io/kndy666/featbench_reflex-dev_reflex:5583

# Clone the repository and checkout the base commit. Then, clean up git history and remove the remote origin to prevent cheating.
RUN git clone https://github.com/reflex-dev/reflex.git /testbed

WORKDIR /testbed

RUN git checkout 60b1baf2c7e41312844de660237c6646a42e9871 && \
    git for-each-ref --format="%(refname:short)" refs/heads/ | xargs -r git branch -D && \
    git checkout -b main && \
    git reflog expire --expire=now --all && \
    git gc --prune=now && \
    git remote remove origin

# Install uv
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
RUN mkdir -p /logs

# Run instance-specific setup commands, if any

