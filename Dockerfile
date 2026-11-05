# One image for every process in the pipeline.
# Build: docker build -t ancestry-aware-variant-report:0.1.0 .
FROM mambaorg/micromamba:1.5.10

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

# Nextflow needs `ps` inside the container to collect task metrics
USER root
RUN apt-get update && apt-get install -y --no-install-recommends procps && \
    rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER

ENV PATH="/opt/conda/bin:${PATH}"
