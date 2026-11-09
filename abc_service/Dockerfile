FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir fastapi==0.115.* "uvicorn[standard]==0.32.*"
COPY main.py .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
