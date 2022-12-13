FROM python:3.9

RUN apt-get update \
    && apt-get install -yq  --no-install-recommends \
              whois ccache \
              libssl-dev libcurl4-openssl-dev \
                  libssh2-1-dev libxml2-dev libcairo2-dev \
                  libsndfile1-dev \
                  ffmpeg \
                  && apt-get clean


COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt

COPY . /

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--workers", "4", "--port", "8000"]