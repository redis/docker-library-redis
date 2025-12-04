FROM python:3.11-slim-trixie

RUN apt update && apt -y install git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    # avoid dubious permissions problem in github CI
    && git config --global --add safe.directory '*' \
    && pip install uv

WORKDIR /release-automation
COPY . /release-automation
RUN uv sync --frozen --no-dev

ENV PATH="/root/.local/bin:${PATH}"
ENV VIRTUAL_ENV="/release-automation/.venv"
ENV PATH="/release-automation/.venv/bin:${PATH}"

ENTRYPOINT ["release-automation"]
CMD ["--help"]
