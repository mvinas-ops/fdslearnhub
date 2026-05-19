#first
sudo nano /etc/nginx/sites-available/fastapi

#second
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

#third
sudo ln -s /etc/nginx/sites-available/fastapi \
           /etc/nginx/sites-enabled/

#forth
pip install gunicorn uvicorn fastapi

#fifth
sudo nano /etc/systemd/system/fastapi.service

#sixth
[Unit]
Description=FastAPI app
After=network.target

[Service]
User=msbongabong
Group=msbongabong
WorkingDirectory=/home/msbongabong/fastapi_app

ExecStart=/home/msbongabong/fastapi_app/venv/bin/gunicorn \
          -w 4 \
          -k uvicorn.workers.UvicornWorker \
          app.main:app \
          --bind 0.0.0.0:8000

Restart=always

[Install]
WantedBy=multi-user.target

#sevent
sudo systemctl daemon-reload
sudo systemctl restart fastapi
sudo systemctl status fastapi

#eight
sudo service nginx start