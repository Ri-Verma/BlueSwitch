docker run -d \
  --name paas-proxy \
  --network paas-network \
  -p 80:80 \
  -v ~/Desktop/WorkStation/MVP/PaaS_System/proxy/conf.d:/etc/nginx/conf.d \
  nginx:alpine
