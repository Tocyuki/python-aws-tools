FROM python:3.8.6-slim

WORKDIR /aws-tools
COPY ./ /aws-tools

RUN pip install -e .
