# Container for free cloud hosting (Render, or a Hugging Face Space). Basic mode: symptom graph, virtual printer, 3D pages; no language model.
# Optional: set DEMO_PASSWORD in the host settings so visitors need a password.
FROM python:3.12-slim

# Hugging Face runs the container as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

RUN pip install --no-cache-dir --user "numpy>=1.24" "openpyxl>=3.1"
COPY --chown=user . .

# STUB=1: no Ollama in the cloud, the assistant runs on the symptom graph alone.
# FMEA_NO_LEARN=1: visitors do not change the saved case memory.
ENV STUB=1 FMEA_NO_LEARN=1 PYTHONUNBUFFERED=1
EXPOSE 7860
# The host gives the port in $PORT (Render); 7860 otherwise (Hugging Face)
CMD python -m src.assistant_v2.server --host 0.0.0.0 --port ${PORT:-7860}
