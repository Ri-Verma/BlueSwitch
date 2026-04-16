docker run -d \
  --name paas-proxy \
  --network paas-network \
  -p 80:80 \
  -v $PWD/conf.d:/etc/nginx/conf.d \
  nginx:alpine
