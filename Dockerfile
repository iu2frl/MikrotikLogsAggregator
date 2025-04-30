FROM python:3.12
WORKDIR /home/bot
COPY ./ .
RUN pip install -r /home/bot/requirements.txt
CMD ["python3", "./main.py"]