FROM python:3.12-slim
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --uid 10001 --create-home clinic
COPY backend ./backend
COPY dist ./dist
RUN mkdir -p work && chown -R clinic:clinic /app
USER clinic
EXPOSE 8784
CMD ["uvicorn","backend.app:app","--host","0.0.0.0","--port","8784"]
